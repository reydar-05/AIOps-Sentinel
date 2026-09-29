"""
Discord Formatter — turns an enriched incident payload into a Discord
webhook message (one rich embed, colour-coded by severity).

Discord embed limits respected here: title 256, description 4096,
field value 1024, max 25 fields.
"""

SEVERITY_COLORS = {
    "CRITICAL": 0xE74C3C,  # red
    "HIGH":     0xE67E22,  # orange
    "MEDIUM":   0xF1C40F,  # yellow
    "LOW":      0x2ECC71,  # green
}
SEVERITY_ICONS = {"CRITICAL": "🚨", "HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟢"}
DEFAULT_COLOR = 0x95A5A6  # grey for UNKNOWN

FIELD_LIMIT = 1024


def _clip(value, limit=FIELD_LIMIT) -> str:
    text = str(value) if value not in (None, "") else "N/A"
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _bullets(items) -> str:
    if isinstance(items, str):
        return _clip(items)
    if not items:
        return "N/A"
    return _clip("\n".join(f"{i}. {a}" for i, a in enumerate(items, 1)))


def format_alert(payload: dict) -> dict:
    """Build a Discord webhook body ({"embeds": [...]}) for an incident."""
    ai = payload.get("ai_analysis", {}) or {}
    severity = str(ai.get("severity", "UNKNOWN")).upper()
    confidence = str(ai.get("confidence", "MEDIUM")).upper()
    components = ai.get("affected_components") or []
    if isinstance(components, str):
        components = [components]

    fields = [
        {"name": "Severity",   "value": f"{SEVERITY_ICONS.get(severity, '⚪')} {severity}", "inline": True},
        {"name": "Confidence", "value": confidence, "inline": True},
        {"name": "Environment", "value": _clip(payload.get("environment", "dev")), "inline": True},
        {"name": "Alarm",      "value": _clip(payload.get("alarm_name")), "inline": True},
        {"name": "Instance",   "value": _clip(payload.get("instance_id")), "inline": True},
        {"name": "Error Type", "value": _clip(payload.get("error_type")), "inline": True},
        {"name": "Root Cause", "value": _clip(ai.get("root_cause")), "inline": False},
        {"name": "Immediate Actions", "value": _bullets(ai.get("immediate_actions")), "inline": False},
        {"name": "Affected Components", "value": _clip(", ".join(components)), "inline": False},
        {"name": "Long-term Fix", "value": _clip(ai.get("long_term_fix")), "inline": False},
        {"name": "Estimated Impact", "value": _clip(ai.get("estimated_impact")), "inline": False},
    ]
    if ai.get("pattern_detected"):
        fields.append({"name": "Pattern Detected",
                       "value": _clip(ai.get("pattern_description")), "inline": False})

    embed = {
        "title": _clip(f"AIOps Sentinel — {severity}: {payload.get('alarm_name', 'Incident')}", 256),
        "description": _clip(ai.get("summary", "No summary available"), 4096),
        "color": SEVERITY_COLORS.get(severity, DEFAULT_COLOR),
        "fields": fields,
        "footer": {"text": f"Incident {payload.get('incident_id', 'N/A')} | {payload.get('region', 'N/A')}"},
        "timestamp": payload.get("timestamp"),
    }
    return {"username": "AIOps Sentinel", "embeds": [embed]}
