"""
Sends a real Slack alert using your webhook URL from .env
Run this to verify end-to-end Slack delivery.

Usage:
    python tests/test_slack_send.py
"""

import sys
import os
from dotenv import load_dotenv

# Load .env explicitly with override=True
dotenv_path = os.path.join(os.path.dirname(__file__), "../.env")
load_dotenv(dotenv_path, override=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lambda/notification_handler"))

os.environ["AWS_REGION"]  = "ap-south-1"
os.environ["ENVIRONMENT"] = "dev"

# Debug — confirm webhook loaded
webhook = os.environ.get("SLACK_WEBHOOK_URL", "NOT FOUND")
print(f"Webhook loaded: {webhook[:50]}...")

from notifier import send_slack_alert

MOCK_ENRICHED = {
    "incident_id":  "live-test-001",
    "timestamp":    "2026-03-21T10:30:00Z",
    "instance_id":  "i-0abc123def456789",
    "asg_name":     "aiops-asg-dev",
    "region":       "ap-south-1",
    "account_id":   "652197206400",
    "event_type":   "CLOUDWATCH_ALARM",
    "alarm_name":   "aiops-high-cpu-dev",
    "alarm_state":  "ALARM",
    "error_type":   "HIGH_CPU",
    "environment":  "dev",
    "ai_analysis": {
        "summary": "Java application crashed due to memory exhaustion causing cascading failures",
        "root_cause": "Java heap space exhaustion in DataProcessor.java triggered OOM, causing Redis connection failures and CPU spike.",
        "severity": "HIGH",
        "severity_reason": "Complete application failure in dev environment",
        "confidence": "HIGH",
        "affected_components": ["EC2", "Auto Scaling Group", "ElastiCache Redis"],
        "immediate_actions": [
            "Increase Java heap size (-Xmx) temporarily",
            "Clear disk space by removing old logs",
            "Restart application server",
            "Scale up ASG"
        ],
        "long_term_fix": "Fix memory leak in DataProcessor.java, add memory monitoring and log rotation",
        "pattern_detected": True,
        "pattern_description": "Memory leaks in DataProcessor.java causing regular OOM — systemic code issue",
        "estimated_impact": "Complete service unavailability for dev environment users"
    }
}

if __name__ == "__main__":
    print("\nSending real Slack alert...")
    success = send_slack_alert(MOCK_ENRICHED)
    if success:
        print("SUCCESS — check your Slack #aiops-alerts channel!")
    else:
        print("FAILED — check your SLACK_WEBHOOK_URL in .env")
        sys.exit(1)
