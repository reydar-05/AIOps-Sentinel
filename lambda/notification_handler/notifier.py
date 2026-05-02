"""
Notifier — sends formatted incident alerts to Discord via webhook.

Routing rules:
  - Normal alerts (HIGH/MEDIUM confidence) go to DISCORD_WEBHOOK_URL.
  - LOW-confidence alerts go to DISCORD_REVIEW_WEBHOOK_URL when configured —
    these need human eyes because the AI didn't have enough log signal.
    If DISCORD_REVIEW_WEBHOOK_URL is unset, low-confidence alerts fall back
    to the normal webhook with a "[REVIEW]" prefix in the embed title.
"""

import copy
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
    analysis = enriched_payload.get("ai_analysis", {})
    severity   = analysis.get("severity", "UNKNOWN")
    confidence = analysis.get("confidence", "MEDIUM").upper()
    is_low_conf = confidence == "LOW"

    logger.info("Dispatching alert | severity: %s | confidence: %s", severity, confidence)

    webhook_url = _select_webhook(is_low_conf)
    if not webhook_url:
        logger.warning("No suitable Discord webhook configured — skipping notification")
        return False

    try:
        # Mark low-confidence alerts in the embed title so the receiving
        # channel makes the "review me" intent unmistakable.
        payload = enriched_payload
        if is_low_conf:
            payload = copy.deepcopy(enriched_payload)
            existing_summary = payload.get("ai_analysis", {}).get("summary", "")
            payload["ai_analysis"]["summary"] = f"[LOW CONFIDENCE — REVIEW] {existing_summary}"

        message = format_discord(payload)
        return _post(webhook_url, message)
    except Exception as e:
        logger.error("Discord send failed: %s", str(e))
        return False


def _select_webhook(is_low_confidence: bool) -> str:
    """
    Pick the webhook URL.
      - LOW confidence + DISCORD_REVIEW_WEBHOOK_URL set → review channel
      - Anything else → main channel (DISCORD_WEBHOOK_URL)
    """
    if is_low_confidence:
        review = os.environ.get("DISCORD_REVIEW_WEBHOOK_URL", "").strip()
        if review and "YOUR/WEBHOOK" not in review:
            logger.info("Routing LOW-confidence alert to review webhook")
            return review
        # Fall through to main webhook with a "[REVIEW]" title prefix.

    main = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if main and "YOUR/WEBHOOK" not in main:
        return main
    return ""


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
