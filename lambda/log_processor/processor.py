"""
Log Processor — orchestrates sanitization, trimming, and metadata enrichment.
Takes raw incident dict → returns AI-ready payload.
"""

import logging
import os
from datetime import datetime, timezone

from log_sanitizer import sanitize
from log_trimmer import trim

logger = logging.getLogger(__name__)


def process(incident: dict) -> dict:
    """
    Full log processing pipeline:
    1. Sanitize  — remove sensitive data
    2. Trim      — cap tokens for the AI model
    3. Enrich    — add structured metadata

    Returns AI-ready payload.
    """
    raw_logs = incident.get("raw_logs", "")

    # ── Step 1: Sanitize ───────────────────────────────────────────
    sanitized_logs = sanitize(raw_logs)
    logger.info("Sanitization complete")

    # ── Step 2: Trim ───────────────────────────────────────────────
    trimmed_logs = trim(sanitized_logs)
    logger.info("Trimming complete — %d chars", len(trimmed_logs))

    # ── Step 3: Classify error type from logs ─────────────────────
    error_type = _classify_error(trimmed_logs, incident)

    # ── Step 4: Build AI-ready payload ────────────────────────────
    payload = {
        # Core identifiers
        "incident_id":   incident.get("incident_id"),
        "timestamp":     incident.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "instance_id":   incident.get("instance_id", "unknown"),
        "asg_name":      incident.get("asg_name"),
        "region":        incident.get("region", "ap-south-1"),
        "account_id":    incident.get("account_id"),

        # Event details
        "event_type":    incident.get("event_type"),
        "alarm_name":    incident.get("alarm_name"),
        "alarm_state":   incident.get("new_state"),
        "alarm_reason":  incident.get("reason"),

        # Processed logs
        "processed_logs":     trimmed_logs,
        "log_char_count":     len(trimmed_logs),
        "log_line_count":     len(trimmed_logs.splitlines()),

        # Derived metadata
        "error_type":         error_type,
        "processed_at":       datetime.now(timezone.utc).isoformat(),
        # Prefer the environment carried by the incident; fall back to the
        # Lambda's own ENVIRONMENT env var only if the incident didn't
        # specify one.
        "environment":        incident.get("environment") or os.environ.get("ENVIRONMENT", "dev"),
    }

    logger.info("Log processing complete for incident %s | error_type: %s",
                payload["incident_id"], payload["error_type"])

    return payload


def _classify_error(logs: str, incident: dict) -> str:
    """
    Quick rule-based error classification from logs + alarm name.
    AI will do deeper analysis — this is a fast pre-classification.
    """
    logs_lower = logs.lower()
    alarm_name = incident.get("alarm_name", "").lower()

    if "cpu" in alarm_name or "cpu" in logs_lower:
        return "HIGH_CPU"
    elif "memory" in alarm_name or "oom" in logs_lower or "out of memory" in logs_lower:
        return "MEMORY_EXHAUSTION"
    elif "disk" in alarm_name or "disk full" in logs_lower or "no space" in logs_lower:
        return "DISK_FULL"
    elif "network" in alarm_name or "connection refused" in logs_lower or "timeout" in logs_lower:
        return "NETWORK_ISSUE"
    elif "status" in alarm_name or incident.get("event_type") == "EC2_STATE_CHANGE":
        return "INSTANCE_FAILURE"
    elif "error" in logs_lower or "exception" in logs_lower:
        return "APPLICATION_ERROR"
    else:
        return "UNKNOWN"
