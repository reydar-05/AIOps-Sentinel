"""
Secure webhook fetcher — retrieves Slack webhook from AWS Secrets Manager.
Never hardcodes secrets. Falls back to env var for local dev only.
"""

import boto3
import json
import logging
import os

logger = logging.getLogger(__name__)

_cache = {}  # In-memory cache — Lambda container reuse saves API calls


def get_slack_webhook() -> dict:
    """
    Returns {"webhook_url": "...", "channel": "..."} from Secrets Manager.
    Falls back to environment variable for local testing.
    """
    secret_name = os.environ.get("SLACK_SECRET_NAME", "aiops/slack/webhook")

    # ── Return cached value if available ──────────────────────────
    if secret_name in _cache:
        logger.debug("Using cached Slack secret")
        return _cache[secret_name]

    # ── Local dev fallback ─────────────────────────────────────────
    local_webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if local_webhook and local_webhook != "https://hooks.slack.com/services/YOUR/WEBHOOK/URL":
        logger.info("Using local SLACK_WEBHOOK_URL env var")
        result = {
            "webhook_url": local_webhook,
            "channel": os.environ.get("SLACK_CHANNEL", "#aiops-alerts")
        }
        _cache[secret_name] = result
        return result

    # ── Fetch from Secrets Manager ─────────────────────────────────
    try:
        client = boto3.client(
            "secretsmanager",
            region_name=os.environ.get("AWS_REGION", "ap-south-1")
        )
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])

        _cache[secret_name] = secret
        logger.info("Slack secret fetched from Secrets Manager")
        return secret

    except Exception as e:
        logger.error("Failed to fetch Slack secret: %s", str(e))
        raise
