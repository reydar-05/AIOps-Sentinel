"""
Notifier — sends formatted Slack alert via webhook.
Fetches webhook securely from Secrets Manager.
"""

import json
import logging
import urllib.request
import urllib.error

from secrets import get_slack_webhook
from slack_formatter import format_alert

logger = logging.getLogger(__name__)


def send_slack_alert(enriched_payload: dict) -> bool:
    """
    Format and send Slack alert for an enriched incident.
    Returns True on success, False on failure.
    """
    try:
        # ── Get webhook URL from Secrets Manager ───────────────────
        secret = get_slack_webhook()
        webhook_url = secret.get("webhook_url")

        if not webhook_url or "REPLACE_ME" in webhook_url:
            logger.warning("Slack webhook not configured — skipping notification")
            return False

        # ── Format the message ─────────────────────────────────────
        message = format_alert(enriched_payload)
        logger.info("Sending Slack alert | severity: %s",
                    enriched_payload.get("ai_analysis", {}).get("severity"))

        # ── POST to Slack ──────────────────────────────────────────
        payload = json.dumps(message).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.getcode()
            body = response.read().decode("utf-8")

        if status == 200 and body == "ok":
            logger.info("Slack alert sent successfully")
            return True
        else:
            logger.error("Slack returned unexpected response: %d — %s", status, body)
            return False

    except urllib.error.HTTPError as e:
        logger.error("Slack webhook HTTP error: %d — %s", e.code, e.read().decode())
        return False

    except Exception as e:
        logger.error("Failed to send Slack alert: %s", str(e))
        return False
