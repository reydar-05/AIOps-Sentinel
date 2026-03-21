"""
Local test for Notification Handler.
Tests formatter locally. Slack send test requires a real webhook URL.

Usage:
    python tests/test_notifications.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lambda/notification_handler"))

os.environ["AWS_REGION"]        = "ap-south-1"
os.environ["ENVIRONMENT"]       = "dev"
os.environ["SLACK_SECRET_NAME"] = "aiops/slack/webhook"
# Set your real Slack webhook here to test actual sending:
os.environ["SLACK_WEBHOOK_URL"] = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

from slack_formatter import format_alert


# ── Mock enriched payload (output of Phase 5) ─────────────────────
MOCK_ENRICHED = {
    "incident_id":    "test-notify-001",
    "timestamp":      "2024-01-15T10:30:00Z",
    "instance_id":    "i-0abc123def456789",
    "asg_name":       "aiops-asg-dev",
    "region":         "ap-south-1",
    "account_id":     "652197206400",
    "event_type":     "CLOUDWATCH_ALARM",
    "alarm_name":     "aiops-high-cpu-dev",
    "alarm_state":    "ALARM",
    "error_type":     "HIGH_CPU",
    "environment":    "dev",
    "ai_analysis": {
        "summary": "Java application crashed due to memory exhaustion causing cascading failures",
        "root_cause": "Java heap space exhaustion in DataProcessor.java triggered OOM, causing Redis connection failures and CPU spike from excessive GC activity.",
        "severity": "HIGH",
        "severity_reason": "Complete application failure in dev environment",
        "confidence": "HIGH",
        "affected_components": ["EC2", "Auto Scaling Group", "ElastiCache Redis", "CloudWatch"],
        "immediate_actions": [
            "Increase Java heap size (-Xmx) temporarily",
            "Clear disk space by removing old logs and heap dumps",
            "Restart application server",
            "Scale up ASG to handle load"
        ],
        "long_term_fix": "Fix memory leak in DataProcessor.java, add memory monitoring, implement log rotation and proper JVM tuning",
        "pattern_detected": True,
        "pattern_description": "Memory leaks in DataProcessor.java causing regular OOM events — systemic code issue",
        "estimated_impact": "Complete service unavailability for dev environment users"
    }
}


def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_formatter_structure():
    print_section("TEST 1: Slack Message Formatter")
    message = format_alert(MOCK_ENRICHED)

    assert "attachments" in message,                    "FAIL: no attachments"
    attachment = message["attachments"][0]
    assert "color" in attachment,                       "FAIL: no color"
    assert attachment["color"] == "#FF6600",            "FAIL: wrong color for HIGH"
    assert "blocks" in attachment,                      "FAIL: no blocks"
    assert len(attachment["blocks"]) >= 6,              "FAIL: too few blocks"

    # Verify header contains severity
    header = attachment["blocks"][0]
    assert "HIGH" in header["text"]["text"],            "FAIL: severity not in header"

    print("PASS: Message structure valid")
    print("PASS: Severity color correct (#FF6600 = orange for HIGH)")
    print("PASS: Block count:", len(attachment["blocks"]))
    print("PASS: Header:", header["text"]["text"])


def test_formatter_content():
    print_section("TEST 2: Message Content Validation")
    message = format_alert(MOCK_ENRICHED)
    message_str = json.dumps(message)

    assert "DataProcessor.java" in message_str,         "FAIL: root cause missing"
    assert "i-0abc123def456789" in message_str,         "FAIL: instance ID missing"
    assert "aiops-high-cpu-dev" in message_str,         "FAIL: alarm name missing"
    assert "Recurring Pattern" in message_str,          "FAIL: pattern warning missing"
    assert "Amazon Bedrock" in message_str,             "FAIL: footer missing"

    print("PASS: Root cause present in message")
    print("PASS: Instance ID present")
    print("PASS: Alarm name present")
    print("PASS: Pattern warning included")
    print("PASS: Footer with Bedrock branding")


def test_severity_colors():
    print_section("TEST 3: Severity Color Routing")
    severities = {
        "CRITICAL": "#FF0000",
        "HIGH":     "#FF6600",
        "MEDIUM":   "#FFD700",
        "LOW":      "#0066CC",
    }

    for severity, expected_color in severities.items():
        payload = {**MOCK_ENRICHED, "ai_analysis": {**MOCK_ENRICHED["ai_analysis"], "severity": severity}}
        message = format_alert(payload)
        color = message["attachments"][0]["color"]
        assert color == expected_color, f"FAIL: {severity} should be {expected_color}, got {color}"
        print(f"PASS: {severity:8} → {color}")


def test_print_full_message():
    print_section("Full Slack Message Preview (JSON)")
    message = format_alert(MOCK_ENRICHED)
    print(json.dumps(message, indent=2)[:1500])
    print("\n  [truncated for display...]")


if __name__ == "__main__":
    print("\nAIOps Sentinel — Notification Tests")
    passed = failed = 0

    for test in [test_formatter_structure, test_formatter_content,
                 test_severity_colors, test_print_full_message]:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\nFAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"\nERROR in {test.__name__}: {e}")
            import traceback; traceback.print_exc()
            failed += 1

    print(f"\n  Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
