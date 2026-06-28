"""Analyze classified items: detect baseline divergence, prepare digest content."""

from observability import (
    BASELINE_DIVERGENCE, HANDOFF, ERROR,
    INFO, WARN, CRITICAL,
    log_event,
)

COMPONENT = "analyze"


def analyze(classified_items: list[dict], baseline: dict | None = None) -> dict:
    """Compare items against baseline and return an analysis report."""
    try:
        report = _build_report(classified_items, baseline)
        if report.get("divergences"):
            log_event(
                BASELINE_DIVERGENCE, WARN, COMPONENT,
                f"{len(report['divergences'])} divergence(s) detected",
                {"count": len(report["divergences"])},
            )
        log_event(HANDOFF, INFO, COMPONENT, "Analysis complete, handing off to output", {"report_keys": list(report.keys())})
        return report
    except Exception as exc:
        log_event(ERROR, CRITICAL, COMPONENT, str(exc), {})
        raise


def _build_report(items: list[dict], baseline: dict | None) -> dict:
    raise NotImplementedError("Analysis logic not yet implemented")
