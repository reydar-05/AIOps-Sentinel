"""
Offline end-to-end test of the Lambda handler: SNS event → parse → logs →
sanitize → AI (stubbed) → DynamoDB (stubbed) → Discord (stubbed).
Usage: python tests/test_pipeline_e2e.py   (or pytest)
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "lambda/incident_processor"))
os.environ.update(AWS_REGION="ap-south-1", ENVIRONMENT="dev", LOG_LEVEL="ERROR",
                  AWS_ACCESS_KEY_ID="x", AWS_SECRET_ACCESS_KEY="x")

import handler  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "lambda_test_event.json")
LOGS = ("[t] ERROR java.lang.OutOfMemoryError: Java heap space from 10.0.1.5\n"
        "[t] INFO password=hunter2 user@corp.com")
AI = {"summary": "OOM", "root_cause": "OutOfMemoryError", "severity": "HIGH", "confidence": "HIGH",
      "affected_components": ["EC2"], "immediate_actions": ["restart"], "long_term_fix": "fix"}


class FakeTable:
    items = []
    def put_item(self, Item): FakeTable.items.append(Item)


def _run(monkeypatch_ai=None):
    sent, FakeTable.items = [], []
    handler.fetch_logs = lambda **kw: LOGS
    handler.dynamodb = type("D", (), {"Table": staticmethod(lambda n: FakeTable())})()
    handler.send_alert = lambda enriched: sent.append(enriched) or True
    handler.analyze = monkeypatch_ai or (lambda p: {**p, "ai_analysis": dict(AI)})
    with open(FIXTURE) as f:
        return handler.lambda_handler(json.load(f), None), sent


def test_happy_path():
    result, sent = _run()
    assert result["statusCode"] == 200 and result["severity"] == "HIGH"
    assert len(FakeTable.items) == 1 and FakeTable.items[0]["status"] == "OPEN"
    logs = sent[0]["processed_logs"]
    assert "10.0.1.5" not in logs and "hunter2" not in logs and "corp.com" not in logs


def test_ai_failure_falls_back_and_still_alerts():
    def boom(p): raise RuntimeError("groq down")
    result, sent = _run(boom)
    assert result["severity"] == "HIGH"
    assert sent[0]["ai_analysis"]["confidence"] == "LOW"
    assert len(FakeTable.items) == 1


def test_unrecognised_event_skipped():
    assert handler.lambda_handler({"Records": []}, None)["body"] == "Event skipped"


if __name__ == "__main__":
    for t in (test_happy_path, test_ai_failure_falls_back_and_still_alerts, test_unrecognised_event_skipped):
        t()
        print(f"PASS: {t.__name__}")
    print("\n  Results: 3 passed, 0 failed")
