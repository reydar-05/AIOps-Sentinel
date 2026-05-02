"""
Fetches recent CloudWatch logs for a given instance/log group.
Falls back gracefully if logs are unavailable.
"""

import boto3
import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

cloudwatch_logs = boto3.client("logs", region_name=os.environ.get("AWS_REGION", "ap-south-1"))


def fetch_logs(instance_id: str | None,
               log_group: str | None,
               lookback_minutes: int = 15) -> str:
    """
    Fetch the last `lookback_minutes` of logs from CloudWatch.
    Returns logs as a single string. Returns placeholder if unavailable.
    """
    if not log_group:
        logger.warning("No log group provided — returning empty logs")
        return "[No log group specified]"

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=lookback_minutes)

    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)

    filter_pattern = ""
    if instance_id:
        filter_pattern = f'"{instance_id}"'

    try:
        response = cloudwatch_logs.filter_log_events(
            logGroupName=log_group,
            startTime=start_ms,
            endTime=end_ms,
            filterPattern=filter_pattern,
            limit=100  # Max 100 lines to stay within AI token limits
        )

        events = response.get("events", [])
        if not events:
            logger.info("No log events found in %s for last %d minutes",
                        log_group, lookback_minutes)
            return f"[No logs found in {log_group} for the last {lookback_minutes} minutes]"

        log_lines = []
        for event in events:
            ts = datetime.fromtimestamp(event["timestamp"] / 1000, tz=timezone.utc)
            log_lines.append(f"[{ts.isoformat()}] {event['message'].strip()}")

        logger.info("Fetched %d log events from %s", len(log_lines), log_group)
        return "\n".join(log_lines)

    except cloudwatch_logs.exceptions.ResourceNotFoundException:
        logger.warning("Log group %s does not exist", log_group)
        return f"[Log group {log_group} not found]"

    except Exception as e:
        logger.error("Failed to fetch logs from %s: %s", log_group, str(e))
        return f"[Log fetch failed: {str(e)}]"
