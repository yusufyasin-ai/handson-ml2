"""Main entry point: orchestrates fetch → classify → analyze → output."""

import sys
import yaml
from pathlib import Path

from observability import NEW_ITEM, HANDOFF, ERROR, INFO, WARN, CRITICAL, log_event
import fetch
import classify
import analyze

COMPONENT = "monitor"

_ROOT = Path(__file__).parent.parent
_SOURCES_PATH = _ROOT / "config" / "sources.yaml"
_POLICY_DIR = _ROOT / "policy"
_STATE_DIR = _ROOT / "state"
_OUTPUT_DIR = _ROOT / "output"


def _load_sources() -> list[dict]:
    with _SOURCES_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)["sources"]


def _load_policy() -> str:
    docs = list(_POLICY_DIR.glob("*.md"))
    if not docs:
        log_event(ERROR, CRITICAL, COMPONENT, "No policy document found in policy/", {})
        sys.exit(1)
    return docs[0].read_text(encoding="utf-8")


def _load_state() -> set[str]:
    seen_file = _STATE_DIR / "seen_ids.txt"
    if not seen_file.exists():
        return set()
    return set(seen_file.read_text(encoding="utf-8").splitlines())


def _save_state(seen: set[str]) -> None:
    _STATE_DIR.mkdir(exist_ok=True)
    (_STATE_DIR / "seen_ids.txt").write_text("\n".join(sorted(seen)), encoding="utf-8")


def run() -> None:
    log_event(HANDOFF, INFO, COMPONENT, "Monitor run started", {})

    sources = _load_sources()
    policy = _load_policy()
    seen = _load_state()

    raw_items = fetch.fetch_all(sources)

    new_items = [it for it in raw_items if it.get("id") not in seen]
    for item in new_items:
        log_event(NEW_ITEM, INFO, COMPONENT, f"New item: {item.get('title', item.get('id'))}", {"id": item.get("id")})

    classified = classify.classify_items(new_items, policy)
    report = analyze.analyze(classified)

    seen.update(it["id"] for it in new_items if "id" in it)
    _save_state(seen)

    log_event(HANDOFF, INFO, COMPONENT, "Monitor run complete", {"new_items": len(new_items)})


if __name__ == "__main__":
    run()
