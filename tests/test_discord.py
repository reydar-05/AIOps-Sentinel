"""
Discord formatter + notifier routing tests. No network required.
Usage: python tests/test_discord.py   (or pytest)
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lambda/notification_handler"))
os.environ.setdefault("AWS_REGION", "ap-south-1")

from discord_formatter import format_alert, SEVERITY_COLORS
import notifier

PAYLOAD = {
    "incident_id": "t-001", "timestamp": "2026-01-15T10:30:00Z", "region": "ap-south-1",
    "alarm_name": "aiops-high-cpu-dev", "instance_id": "i-0abc", "error_type": "HIGH_CPU",
    "environment": "dev",
    "ai_analysis": {
        "summary": "OOM killed the app", "root_cause": "java.lang.OutOfMemoryError",
        "severity": "HIGH", "confidence": "HIGH", "affected_components": ["EC2"],
        "immediate_actions": ["Restart service", "Raise heap"], "long_term_fix": "Fix leak",
        "pattern_detected": True, "pattern_description": "Every 2h", "estimated_impact": "Outage",
    },
}


def test_embed_structure():
    msg = format_alert(PAYLOAD)
    embed = msg["embeds"][0]
    assert embed["color"] == SEVERITY_COLORS["HIGH"]
    assert "aiops-high-cpu-dev" in json.dumps(msg) and "i-0abc" in json.dumps(msg)
    assert len(embed["fields"]) <= 25
    assert all(len(f["value"]) <= 1024 for f in embed["fields"])


def test_all_severities_and_missing_data():
    for sev in SEVERITY_COLORS:
        p = {**PAYLOAD, "ai_analysis": {**PAYLOAD["ai_analysis"], "severity": sev}}
        assert format_alert(p)["embeds"][0]["color"] == SEVERITY_COLORS[sev]
    assert format_alert({})["embeds"][0]["fields"]  # must not crash on empty payload


def test_long_values_are_clipped():
    p = {**PAYLOAD, "ai_analysis": {**PAYLOAD["ai_analysis"], "root_cause": "x" * 5000}}
    assert all(len(f["value"]) <= 1024 for f in format_alert(p)["embeds"][0]["fields"])


def test_low_confidence_routing(monkeypatch=None):
    os.environ["DISCORD_WEBHOOK_URL"] = "https://discord.test/main"
    os.environ["DISCORD_REVIEW_WEBHOOK_URL"] = "https://discord.test/review"
    assert notifier._select_webhook(True) == "https://discord.test/review"
    assert notifier._select_webhook(False) == "https://discord.test/main"
    os.environ["DISCORD_REVIEW_WEBHOOK_URL"] = ""
    assert notifier._select_webhook(True) == "https://discord.test/main"
    os.environ["DISCORD_WEBHOOK_URL"] = ""
    assert notifier.send_alert(PAYLOAD) is False  # unconfigured → graceful False


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\n  Results: {len(tests)} passed, 0 failed")
