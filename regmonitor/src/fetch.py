"""Fetch items from configured regulatory sources."""

from observability import (
    SOURCE_FAILURE, PARSE_OK, ERROR,
    INFO, WARN, CRITICAL,
    log_event,
)

COMPONENT = "fetch"


def fetch_all(sources: list[dict]) -> list[dict]:
    """Fetch items from all enabled sources. Returns a flat list of raw items."""
    items = []
    for source in sources:
        if not source.get("enabled", True):
            continue
        try:
            fetched = _fetch_source(source)
            log_event(PARSE_OK, INFO, COMPONENT, f"Fetched {len(fetched)} items", {"source": source["name"]})
            items.extend(fetched)
        except Exception as exc:
            log_event(SOURCE_FAILURE, CRITICAL, COMPONENT, str(exc), {"source": source.get("name")})
    return items


def _fetch_source(source: dict) -> list[dict]:
    raise NotImplementedError("Fetch logic not yet implemented")
