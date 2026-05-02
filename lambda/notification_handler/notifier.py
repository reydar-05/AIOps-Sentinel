"""
Notifier — sends formatted incident alerts to Discord via webhook.
"""

import json
import logging
import os
import urllib.request
import urllib.error

from discord_formatter import format_alert as format_discord

logger = logging.getLogger(__name__)


def send_alert(enriched_payload: dict) -> bool:
    """
    Format and send a Discord alert for an enriched incident.
    Returns True on success, False on failure or unconfigured webhook.
    """
    severity = enriched_payload.get("ai_analysis", {}).get("severity", "UNKNOWN")
    logger.info("Dispatching alert | severity: %s", severity)

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url or "YOUR/WEBHOOK" in webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL not configured — skipping notification")
        return False

    try:
        message = format_discord(enriched_payload)
        return _post(webhook_url, message)
    except Exception as e:
        logger.error("Discord send failed: %s", str(e))
        return False


def _post(url: str, message: dict) -> bool:
    """POST a Discord webhook payload. Returns True on 204 No Content."""
    try:
        payload = json.dumps(message).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AIOps-Sentinel/1.0",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.getcode()
            body = response.read().decode("utf-8")

        if status == 204:
            logger.info("Discord alert sent successfully")
            return True

        logger.error("Discord returned unexpected response: %d — %s", status, body[:200])
        return False

    except urllib.error.HTTPError as e:
        logger.error("Discord webhook HTTP error: %d — %s", e.code, e.read().decode()[:200])
        return False
