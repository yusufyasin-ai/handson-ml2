"""Classify fetched items against the loaded policy."""

from observability import (
    CLASSIFICATION, LOW_CONFIDENCE, VALIDATOR_DISAGREEMENT, ERROR,
    INFO, WARN, CRITICAL,
    log_event,
)

COMPONENT = "classify"

LOW_CONFIDENCE_THRESHOLD = 0.6


def classify_items(items: list[dict], policy: str) -> list[dict]:
    """Classify each item and return annotated records."""
    results = []
    for item in items:
        try:
            result = _classify_one(item, policy)
            severity = WARN if result["confidence"] < LOW_CONFIDENCE_THRESHOLD else INFO
            log_event(
                LOW_CONFIDENCE if result["confidence"] < LOW_CONFIDENCE_THRESHOLD else CLASSIFICATION,
                severity,
                COMPONENT,
                f"Classified item: {item.get('title', item.get('id'))}",
                {"confidence": result["confidence"], "label": result["label"]},
            )
            results.append({**item, **result})
        except Exception as exc:
            log_event(ERROR, CRITICAL, COMPONENT, str(exc), {"item_id": item.get("id")})
    return results


def _classify_one(item: dict, policy: str) -> dict:
    raise NotImplementedError("Classification logic not yet implemented")
