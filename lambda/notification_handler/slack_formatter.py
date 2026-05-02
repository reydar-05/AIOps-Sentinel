"""
Slack message formatter — builds rich Block Kit payloads.
Severity-aware formatting: CRITICAL gets red, HIGH gets orange, etc.
"""

from datetime import datetime, timezone

# ── Severity styling ───────────────────────────────────────────────
SEVERITY_CONFIG = {
    "CRITICAL": {"emoji": ":rotating_light:", "color": "#FF0000", "label": "CRITICAL"},
    "HIGH":     {"emoji": ":red_circle:",      "color": "#FF6600", "label": "HIGH"},
    "MEDIUM":   {"emoji": ":large_yellow_circle:", "color": "#FFD700", "label": "MEDIUM"},
    "LOW":      {"emoji": ":large_blue_circle:",   "color": "#0066CC", "label": "LOW"},
}


def format_alert(enriched_payload: dict) -> dict:
    """
    Build a Slack Block Kit message from enriched incident payload.
    Returns a dict ready to POST to Slack webhook.
    """
    analysis = enriched_payload.get("ai_analysis", {})
    severity = analysis.get("severity", "HIGH").upper()
    config   = SEVERITY_CONFIG.get(severity, SEVERITY_CONFIG["HIGH"])

    incident_id  = enriched_payload.get("incident_id", "unknown")
    instance_id  = enriched_payload.get("instance_id", "N/A")
    alarm_name   = enriched_payload.get("alarm_name", "unknown")
    region       = enriched_payload.get("region", "ap-south-1")
    environment  = enriched_payload.get("environment", "dev").upper()
    timestamp    = enriched_payload.get("timestamp", datetime.now(timezone.utc).isoformat())

    summary      = analysis.get("summary", "No summary available")
    root_cause   = analysis.get("root_cause", "Unknown")
    confidence   = analysis.get("confidence", "MEDIUM")
    impact       = analysis.get("estimated_impact", "Unknown")
    long_term    = analysis.get("long_term_fix", "Not provided")

    actions      = analysis.get("immediate_actions", [])
    components   = analysis.get("affected_components", [])
    pattern      = analysis.get("pattern_detected", False)
    pattern_desc = analysis.get("pattern_description", "")

    # ── Format immediate actions list ──────────────────────────────
    actions_text = "\n".join([f"  {i+1}. {a}" for i, a in enumerate(actions[:4])])
    components_text = ", ".join(components[:5]) if components else "Unknown"

    # ── Build Slack Block Kit payload ──────────────────────────────
    blocks = [
        # ── Header ────────────────────────────────────────────────
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{config['emoji']} AIOps Sentinel Alert — {severity}",
                "emoji": True
            }
        },

        # ── Summary banner ─────────────────────────────────────────
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{summary}*"
            }
        },

        {"type": "divider"},

        # ── Incident metadata ──────────────────────────────────────
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Incident ID*\n`{incident_id[:18]}...`"},
                {"type": "mrkdwn", "text": f"*Environment*\n{environment}"},
                {"type": "mrkdwn", "text": f"*Alarm*\n`{alarm_name}`"},
                {"type": "mrkdwn", "text": f"*Instance*\n`{instance_id}`"},
                {"type": "mrkdwn", "text": f"*Region*\n{region}"},
                {"type": "mrkdwn", "text": f"*Confidence*\n{confidence}"},
            ]
        },

        {"type": "divider"},

        # ── Root cause ─────────────────────────────────────────────
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":mag: *Root Cause*\n{root_cause}"
            }
        },

        # ── Immediate actions ──────────────────────────────────────
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":hammer_and_wrench: *Immediate Actions*\n{actions_text}"
            }
        },

        # ── Long-term fix ──────────────────────────────────────────
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":building_construction: *Long-term Fix*\n{long_term}"
            }
        },

        {"type": "divider"},

        # ── Impact + components ────────────────────────────────────
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Estimated Impact*\n{impact}"},
                {"type": "mrkdwn", "text": f"*Affected Components*\n{components_text}"},
            ]
        },
    ]

    # ── Pattern warning (only if detected) ────────────────────────
    if pattern and pattern_desc:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":warning: *Recurring Pattern Detected*\n{pattern_desc}"
            }
        })

    # ── Footer ────────────────────────────────────────────────────
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"AIOps Sentinel | {timestamp} | Powered by Groq Llama"
            }
        ]
    })

    return {
        "attachments": [
            {
                "color": config["color"],
                "blocks": blocks
            }
        ]
    }
