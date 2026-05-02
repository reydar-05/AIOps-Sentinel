"""
AIOps Sentinel — Master Lambda Handler
Full pipeline: Parse → Process Logs → AI Analysis → Notify

Triggered by SNS (CloudWatch Alarm or EC2 state change via EventBridge)
"""

import json
import os
import logging
import sys

# ── Path setup for local imports ───────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../log_processor"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ai_analyzer"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../notification_handler"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../ai/prompts"))

from event_parser import parse_event
from log_fetcher import fetch_logs
from processor import process
from analyzer import analyze
from notifier import send_slack_alert

import boto3

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "ap-south-1"))


def lambda_handler(event, context):
    """
    Master pipeline handler.
    1. Parse SNS event
    2. Fetch CloudWatch logs
    3. Process + sanitize logs
    4. AI root cause analysis
    5. Save incident to DynamoDB
    6. Send Slack alert
    """
    logger.info("AIOps Sentinel triggered | requestId: %s",
                context.aws_request_id if context else "local")
    logger.debug("Raw event: %s", json.dumps(event))

    try:
        # ── 1. Parse event ─────────────────────────────────────────
        incident = parse_event(event)
        if not incident:
            logger.warning("Unrecognized event — skipping")
            return {"statusCode": 200, "body": "Event skipped"}

        logger.info("Incident parsed: %s | type: %s",
                    incident["incident_id"], incident["event_type"])

        # ── 2. Fetch logs ──────────────────────────────────────────
        logs = fetch_logs(
            instance_id=incident.get("instance_id"),
            log_group=incident.get("log_group"),
            lookback_minutes=15
        )
        incident["raw_logs"] = logs

        # ── 3. Process + sanitize logs ─────────────────────────────
        payload = process(incident)
        logger.info("Logs processed: %d chars", payload["log_char_count"])

        # ── 4. AI analysis ─────────────────────────────────────────
        try:
            enriched = analyze(payload)
            severity = enriched.get("ai_analysis", {}).get("severity", "UNKNOWN")
            logger.info("AI analysis complete | severity: %s", severity)
        except Exception as ai_err:
            logger.warning("AI analysis unavailable — using fallback: %s", str(ai_err))
            enriched = dict(payload)
            enriched["ai_analysis"] = {
                "summary": "AI analysis unavailable — manual review required",
                "root_cause": "Groq AI analysis could not be completed at this time",
                "severity": "HIGH",
                "severity_reason": "Defaulted to HIGH — AI unavailable",
                "affected_components": [payload.get("error_type", "unknown")],
                "immediate_actions": [
                    "Review CloudWatch logs manually",
                    "Check the affected instance or service",
                    "Escalate if issue persists"
                ],
                "long_term_fix": "Restore Groq API access for automated analysis",
                "pattern_detected": False,
                "pattern_description": None,
                "confidence": "LOW",
                "estimated_impact": "Unknown — manual review needed"
            }
            severity = "HIGH"

        # ── 5. Save to DynamoDB ────────────────────────────────────
        _save_incident(enriched)

        # ── 6. Send Slack alert ────────────────────────────────────
        send_slack_alert(enriched)

        logger.info("Pipeline complete for incident: %s", incident["incident_id"])

        return {
            "statusCode": 200,
            "incident_id": incident["incident_id"],
            "severity": severity
        }

    except Exception as e:
        logger.error("Pipeline failed: %s", str(e), exc_info=True)
        raise  # Re-raise so DLQ captures it


def _save_incident(enriched: dict):
    """Persist incident to DynamoDB."""
    table_name = os.environ.get("DYNAMODB_TABLE_NAME", "aiops-incidents-dev")

    try:
        table = dynamodb.Table(table_name)
        analysis = enriched.get("ai_analysis", {})

        table.put_item(Item={
            "incident_id":  enriched["incident_id"],
            "timestamp":    enriched["timestamp"],
            "alarm_name":   enriched.get("alarm_name", "unknown"),
            "instance_id":  enriched.get("instance_id", "unknown"),
            "severity":     analysis.get("severity", "UNKNOWN"),
            "error_type":   enriched.get("error_type", "UNKNOWN"),
            "summary":      analysis.get("summary", ""),
            "root_cause":   analysis.get("root_cause", ""),
            "environment":  enriched.get("environment", "dev"),
            "status":       "OPEN",
            "ttl":          _ttl_30_days()
        })
        logger.info("Incident saved to DynamoDB: %s", enriched["incident_id"])

    except Exception as e:
        logger.error("DynamoDB save failed: %s", str(e))
        # Don't raise — DynamoDB failure shouldn't block Slack alert


def _ttl_30_days() -> int:
    """Returns Unix timestamp 30 days from now for DynamoDB TTL."""
    from datetime import datetime, timezone, timedelta
    return int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
