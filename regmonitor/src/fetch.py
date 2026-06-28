"""Fetch regulatory items from configured HTML sources.

Each source is fully described by its config/sources.yaml entry —
no per-source code required. Parser hints (CSS selectors + field extractors)
drive BeautifulSoup. A liveness check gates every source: if the parsed
item count is below min_items we emit SOURCE_FAILURE/critical and exclude
the source from the run. A silent empty parse is never reported as clean.

State lives in state/<slug>.json as a list of short SHA-256 hashes (title+link).
Per-source isolation means a new source starts fresh without touching others.
"""

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from observability import (
    SOURCE_FAILURE, PARSE_OK, NEW_ITEM, ERROR,
    INFO, WARN, CRITICAL,
    log_event,
)

COMPONENT = "fetch"

_ROOT = Path(__file__).parent.parent
_STATE_DIR = _ROOT / "state"

_DEFAULT_TIMEOUT = 30
_DEFAULT_MIN_ITEMS = 1
_HEADERS = {
    "User-Agent": (
        "RegMonitor/1.0 (regulatory-compliance monitoring bot; "
        "contact the operator if you have questions)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


# ---------------------------------------------------------------------------
# State helpers (per-source JSON list of hashes)
# ---------------------------------------------------------------------------

def _slug_from_source(source: dict) -> str:
    raw = source.get("slug") or re.sub(r"[^a-z0-9]+", "_", source["name"].lower()).strip("_")
    return raw


def _state_path(slug: str) -> Path:
    return _STATE_DIR / f"{slug}.json"


def _load_state(slug: str) -> set[str]:
    path = _state_path(slug)
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError) as exc:
        log_event(ERROR, WARN, COMPONENT, f"Could not read state for {slug}: {exc}", {"slug": slug})
        return set()


def _save_state(slug: str, seen: set[str]) -> None:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    _state_path(slug).write_text(
        json.dumps(sorted(seen), indent=2), encoding="utf-8"
    )


def _item_hash(title: str, link: str) -> str:
    key = f"{title.strip()}||{link.strip()}"
    return hashlib.sha256(key.encode()).hexdigest()[:20]


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------

def _extract_field(row, field_cfg: dict, base_url: str) -> str:
    """Pull one field value from a BeautifulSoup element using config hints."""
    selector = field_cfg.get("selector", "")
    attr = field_cfg.get("attr", "text")

    target = row.select_one(selector) if selector else row
    if target is None:
        return ""

    if attr == "text":
        return target.get_text(" ", strip=True)

    value = target.get(attr, "") or ""
    if attr == "href" and value and not value.startswith(("http://", "https://")):
        value = urljoin(base_url, value)
    return value.strip()


# ---------------------------------------------------------------------------
# Single-source fetch + parse
# ---------------------------------------------------------------------------

def _fetch_source(source: dict) -> tuple[list[dict], bool]:
    """Fetch and parse one source. Returns (items, liveness_ok).

    liveness_ok is False when the HTTP request fails OR when the parsed
    count is below min_items. In either case SOURCE_FAILURE is already logged.
    """
    name = source["name"]
    url = source["url"]
    parser = source.get("parser", {})
    min_items: int = source.get("liveness", {}).get("min_items", _DEFAULT_MIN_ITEMS)
    slug = _slug_from_source(source)

    # --- HTTP fetch ---
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_DEFAULT_TIMEOUT)
        resp.raise_for_status()
    except requests.Timeout:
        log_event(
            SOURCE_FAILURE, CRITICAL, COMPONENT,
            f"Timeout fetching {name} after {_DEFAULT_TIMEOUT}s",
            {"source": name, "url": url},
        )
        return [], False
    except requests.RequestException as exc:
        log_event(
            SOURCE_FAILURE, CRITICAL, COMPONENT,
            f"HTTP error fetching {name}: {exc}",
            {"source": name, "url": url, "error": str(exc)},
        )
        return [], False

    # --- Parse ---
    item_selector = parser.get("item_selector", "")
    fields_cfg = parser.get("fields", {})

    if not item_selector or item_selector == "TODO":
        log_event(
            SOURCE_FAILURE, CRITICAL, COMPONENT,
            f"item_selector not configured for {name} — skipping",
            {"source": name},
        )
        return [], False

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select(item_selector)

    items: list[dict] = []
    for row in rows:
        title = _extract_field(row, fields_cfg.get("title", {}), url)
        date = _extract_field(row, fields_cfg.get("date", {}), url)
        link = _extract_field(row, fields_cfg.get("link", {"attr": "href"}), url)

        if not title and not link:
            continue  # skip completely empty rows (e.g. header rows selected by mistake)

        items.append(
            {
                "title": title,
                "date": date,
                "link": link,
                "source": name,
                "source_slug": slug,
                "tags": source.get("tags", []),
            }
        )

    # --- Liveness check ---
    if len(items) < min_items:
        log_event(
            SOURCE_FAILURE, CRITICAL, COMPONENT,
            (
                f"Liveness FAILED for {name}: parsed {len(items)} item(s), "
                f"threshold is {min_items}. "
                "Zero items or a broken selector must not be treated as 'no new circulars'."
            ),
            {"source": name, "parsed": len(items), "min_items": min_items, "url": url},
        )
        return items, False

    log_event(
        PARSE_OK, INFO, COMPONENT,
        f"Parsed {len(items)} items from {name}",
        {"source": name, "item_count": len(items)},
    )
    return items, True


# ---------------------------------------------------------------------------
# Diff against state
# ---------------------------------------------------------------------------

def _diff_and_commit(items: list[dict], slug: str) -> list[dict]:
    """Return only genuinely new items; persist updated state immediately.

    State is committed before classification so that a classification failure
    on run N does not re-surface the same items on run N+1 (which would cause
    duplicate digest entries). Operators can query LOW_CONFIDENCE/ERROR logs
    to identify items that need manual review.
    """
    seen = _load_state(slug)
    new_items = []

    for item in items:
        h = _item_hash(item.get("title", ""), item.get("link", ""))
        if h not in seen:
            item["_hash"] = h
            new_items.append(item)

    if new_items:
        updated = seen | {it["_hash"] for it in new_items}
        _save_state(slug, updated)

    for item in new_items:
        log_event(
            NEW_ITEM, INFO, COMPONENT,
            f"New item: {item['title'][:100] or item['link']}",
            {
                "source": item["source"],
                "title": item["title"],
                "link": item["link"],
                "date": item.get("date", ""),
            },
        )

    return new_items


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_all(sources: list[dict]) -> tuple[list[dict], list[str], list[str]]:
    """Fetch all enabled sources.

    Returns:
        new_items      – flat list of items not seen in previous runs
        healthy        – source names that passed liveness
        failed         – source names that failed liveness (excluded from digest)
    """
    all_new: list[dict] = []
    healthy: list[str] = []
    failed: list[str] = []

    for source in sources:
        if not source.get("enabled", True):
            continue

        name = source["name"]
        slug = _slug_from_source(source)

        items, liveness_ok = _fetch_source(source)

        if not liveness_ok:
            failed.append(name)
            continue

        healthy.append(name)
        new_items = _diff_and_commit(items, slug)
        all_new.extend(new_items)

    return all_new, healthy, failed
