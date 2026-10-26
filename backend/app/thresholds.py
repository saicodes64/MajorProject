"""Status / threshold configuration.

The MetroPT-3 documentation does NOT define operational alarm thresholds, so we
do NOT invent any. Status is computed from an EXPLICIT, configurable table here.
By default every tag resolves to the neutral status "Monitoring".

To enable real Normal/Warning/Critical bands later (or once proper anomaly
detection lands), add an entry to ``THRESHOLDS`` keyed by tag_name:

    "Oil_temperature": {"warning": 80.0, "critical": 85.0}

``warning``/``critical`` are upper bounds (value >= critical -> Critical, etc.).
This structure is intentionally simple and is the single explicit place where
thresholds live until the anomaly-detection phase replaces it.
"""
from __future__ import annotations

# Empty by default — no invented thresholds. Fill in per tag_name when known.
THRESHOLDS: dict[str, dict[str, float]] = {}

STATUS_MONITORING = "Monitoring"
STATUS_NORMAL = "Normal"
STATUS_WARNING = "Warning"
STATUS_CRITICAL = "Critical"
STATUS_UNKNOWN = "Unknown"


def compute_status(tag_name: str, value: float | None) -> str:
    """Return a status band for a tag value using the explicit THRESHOLDS table.

    With no configured thresholds (the current default), returns "Monitoring" —
    a neutral status indicating the tag is being observed without alarm limits.
    """
    if value is None:
        return STATUS_UNKNOWN

    cfg = THRESHOLDS.get(tag_name)
    if not cfg:
        return STATUS_MONITORING

    critical = cfg.get("critical")
    warning = cfg.get("warning")
    if critical is not None and value >= critical:
        return STATUS_CRITICAL
    if warning is not None and value >= warning:
        return STATUS_WARNING
    return STATUS_NORMAL
