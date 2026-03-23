"""
Parses raw SNS/EventBridge events into a normalized incident dict.
Handles two event types:
  1. CloudWatch Alarm    (metric breach)
  2. EC2 State Change    (instance stopped/terminated)
"""

import json
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def parse_event(raw_event: dict) -> dict | None:
    """
    Entry point — detects event type and routes to correct parser.
    Returns a normalized incident dict or None if unrecognized.
    """
    records = raw_event.get("Records", [])

    if not records:
        logger.warning("No Records in event")
        return None

    # SNS wraps the real message inside Records[0].Sns.Message
    sns_record = records[0].get("Sns", {})
    message_str = sns_record.get("Message", "{}")

    try:
        message = json.loads(message_str)
    except json.JSONDecodeError:
        logger.error("Could not parse SNS message as JSON: %s", message_str)
        return None

    # ── Route by event source ──────────────────────────────────────
    source = message.get("source", "")
    detail_type = message.get("detail-type", "")
    alarm_name = message.get("AlarmName", "")

    if alarm_name:
        return _parse_cloudwatch_alarm(message, sns_record)
    elif source == "aws.ec2" or detail_type == "EC2 Instance State-change Notification":
        return _parse_ec2_state_change(message, sns_record)
    else:
        logger.warning("Unrecognized event type — source: %s, detail-type: %s",
                       source, detail_type)
        return None


def _parse_cloudwatch_alarm(message: dict, sns_record: dict) -> dict:
    """Parse a CloudWatch Alarm state change notification."""
    alarm_name = message.get("AlarmName", "unknown-alarm")
    new_state = message.get("NewStateValue", "UNKNOWN")
    old_state = message.get("OldStateValue", "UNKNOWN")
    reason = message.get("NewStateReason", "No reason provided")
    timestamp = message.get("StateChangeTime", datetime.now(timezone.utc).isoformat())

    # Extract instance ID from alarm dimensions if present
    trigger = message.get("Trigger", {})
    dimensions = trigger.get("Dimensions", [])
    instance_id = None
    asg_name = None

    for dim in dimensions:
        if dim.get("name") == "InstanceId":
            instance_id = dim.get("value")
        if dim.get("name") == "AutoScalingGroupName":
            asg_name = dim.get("value")

    # Derive log group from alarm name
    log_group = "/aws/ec2/aiops" if instance_id else "/aws/lambda/aiops-incident-processor-dev"

    return {
        "incident_id": str(uuid.uuid4()),
        "event_type": "CLOUDWATCH_ALARM",
        "alarm_name": alarm_name,
        "instance_id": instance_id,
        "asg_name": asg_name,
        "new_state": new_state,
        "old_state": old_state,
        "reason": reason,
        "timestamp": timestamp,
        "log_group": log_group,
        "region": message.get("Region", "ap-south-1"),
        "account_id": message.get("AWSAccountId", ""),
        "sns_topic_arn": sns_record.get("TopicArn", ""),
        "raw_message": message
    }


def _parse_ec2_state_change(message: dict, sns_record: dict) -> dict:
    """Parse an EC2 instance state change event from EventBridge."""
    detail = message.get("detail", {})
    instance_id = detail.get("instance-id", "unknown")
    state = detail.get("state", "unknown")
    timestamp = message.get("time", datetime.now(timezone.utc).isoformat())
    region = message.get("region", "ap-south-1")

    return {
        "incident_id": str(uuid.uuid4()),
        "event_type": "EC2_STATE_CHANGE",
        "alarm_name": f"EC2StateChange-{instance_id}",
        "instance_id": instance_id,
        "asg_name": None,
        "new_state": state.upper(),
        "old_state": "RUNNING",
        "reason": f"EC2 instance {instance_id} transitioned to {state}",
        "timestamp": timestamp,
        "log_group": "/aws/ec2/aiops",
        "region": region,
        "account_id": message.get("account", ""),
        "sns_topic_arn": sns_record.get("TopicArn", ""),
        "raw_message": message
    }
