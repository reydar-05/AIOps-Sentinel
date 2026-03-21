"""
Local test script for Lambda incident processor.
Run this in VS Code terminal — no AWS deployment needed.

Usage:
    python tests/test_local_lambda.py
"""

import json
import sys
import os

# Add lambda path so imports work locally
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lambda/incident_processor"))

# Set env vars before importing handler
os.environ["AWS_REGION"] = "ap-south-1"
os.environ["LOG_LEVEL"] = "INFO"
os.environ["ENVIRONMENT"] = "dev"

from event_parser import parse_event

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(filename: str) -> dict:
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path) as f:
        return json.load(f)


def print_section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_cloudwatch_alarm_parsing():
    print_section("TEST 1: CloudWatch Alarm Event")
    event = load_fixture("mock_cloudwatch_alarm_event.json")
    incident = parse_event(event)

    assert incident is not None, "FAIL: parse_event returned None"
    assert incident["event_type"] == "CLOUDWATCH_ALARM", "FAIL: wrong event type"
    assert incident["alarm_name"] == "aiops-high-cpu-dev", "FAIL: wrong alarm name"
    assert incident["new_state"] == "ALARM", "FAIL: wrong state"
    assert incident["incident_id"] is not None, "FAIL: no incident ID"

    print("PASS: Event type     →", incident["event_type"])
    print("PASS: Alarm name     →", incident["alarm_name"])
    print("PASS: State          →", incident["new_state"])
    print("PASS: Incident ID    →", incident["incident_id"])
    print("PASS: Reason         →", incident["reason"][:80], "...")
    print("PASS: ASG name       →", incident["asg_name"])
    print("PASS: Timestamp      →", incident["timestamp"])


def test_ec2_state_change_parsing():
    print_section("TEST 2: EC2 State Change Event")
    event = load_fixture("mock_ec2_state_change_event.json")
    incident = parse_event(event)

    assert incident is not None, "FAIL: parse_event returned None"
    assert incident["event_type"] == "EC2_STATE_CHANGE", "FAIL: wrong event type"
    assert incident["instance_id"] == "i-0abc123def456789", "FAIL: wrong instance ID"
    assert incident["new_state"] == "STOPPED", "FAIL: wrong state"

    print("PASS: Event type     →", incident["event_type"])
    print("PASS: Instance ID    →", incident["instance_id"])
    print("PASS: State          →", incident["new_state"])
    print("PASS: Incident ID    →", incident["incident_id"])
    print("PASS: Reason         →", incident["reason"])
    print("PASS: Region         →", incident["region"])


def test_invalid_event():
    print_section("TEST 3: Invalid / Empty Event")
    event = {"Records": [{"Sns": {"Message": "not-valid-json"}}]}
    incident = parse_event(event)
    assert incident is None, "FAIL: should return None for invalid event"
    print("PASS: Invalid event correctly returned None")


if __name__ == "__main__":
    print("\nAIOps Sentinel — Lambda Local Tests")
    print("Running without AWS deployment...\n")

    passed = 0
    failed = 0

    tests = [
        test_cloudwatch_alarm_parsing,
        test_ec2_state_change_parsing,
        test_invalid_event,
    ]

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ {e}")
            failed += 1
        except Exception as e:
            print(f"\n💥 Unexpected error in {test.__name__}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
