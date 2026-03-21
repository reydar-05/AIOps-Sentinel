"""
Local tests for Log Processing Engine.

Usage:
    python tests/test_log_processor.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lambda/log_processor"))

os.environ["ENVIRONMENT"] = "dev"
os.environ["AWS_REGION"] = "ap-south-1"

from log_sanitizer import sanitize
from log_trimmer import trim
from processor import process


def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ── Shared mock incident ───────────────────────────────────────────
MOCK_INCIDENT = {
    "incident_id": "test-1234",
    "event_type": "CLOUDWATCH_ALARM",
    "alarm_name": "aiops-high-cpu-dev",
    "instance_id": "i-0abc123def456789",
    "asg_name": "aiops-asg-dev",
    "new_state": "ALARM",
    "old_state": "OK",
    "reason": "CPU exceeded 80%",
    "timestamp": "2024-01-15T10:30:00Z",
    "region": "ap-south-1",
    "account_id": "652197206400",
    "raw_logs": """[2024-01-15T10:28:00Z] INFO  Starting application server on 10.0.1.45:8080
[2024-01-15T10:28:30Z] INFO  Connected to DB at 10.0.2.100:5432
[2024-01-15T10:29:00Z] ERROR Exception in thread main: java.lang.OutOfMemoryError: Java heap space
[2024-01-15T10:29:01Z] ERROR   at com.app.service.DataProcessor.process(DataProcessor.java:142)
[2024-01-15T10:29:02Z] CRITICAL password=SuperSecret123 token=eyJhbGciOiJIUzI1NiJ9.abc
[2024-01-15T10:29:10Z] ERROR Connection refused to 10.0.3.50:6379 (Redis)
[2024-01-15T10:29:15Z] INFO  Retry attempt 1/3 for user admin@company.com
[2024-01-15T10:29:30Z] FATAL Process killed: Out Of Memory
[2024-01-15T10:29:45Z] ERROR Disk usage at 98% on /dev/xvda1
[2024-01-15T10:30:00Z] CRITICAL CPU utilization: 92.5%"""
}


def test_sanitizer():
    print_section("TEST 1: Log Sanitizer")
    logs = MOCK_INCIDENT["raw_logs"]
    result = sanitize(logs)

    print("Input sample:  ", logs.splitlines()[1])
    print("Output sample: ", result.splitlines()[1])

    assert "[IP_REDACTED]" in result,          "FAIL: IP not redacted"
    assert "10.0.1.45" not in result,          "FAIL: raw IP still present"
    assert "[CREDENTIAL_REDACTED]" in result,  "FAIL: credentials not redacted"
    assert "SuperSecret123" not in result,     "FAIL: password still present"
    assert "[EMAIL_REDACTED]" in result,       "FAIL: email not redacted"
    assert "admin@company.com" not in result,  "FAIL: email still present"

    print("PASS: IPs redacted")
    print("PASS: Credentials redacted")
    print("PASS: Emails redacted")
    print("\nSanitized output:")
    for line in result.splitlines():
        print("  ", line)


def test_trimmer():
    print_section("TEST 2: Log Trimmer")
    # Generate a large log — each line ~100 chars to force char-level trimming
    big_log = "\n".join([
        f"[2024-01-15T10:00:{i:02d}Z] INFO Normal log line {i} " + "x" * 60
        for i in range(200)
    ])
    big_log += "\n[2024-01-15T10:03:00Z] ERROR Critical failure detected"

    result = trim(big_log)

    assert len(result) < len(big_log),         "FAIL: logs not shortened at all"
    assert "Critical failure" in result,        "FAIL: priority line dropped"
    assert "Normal log line 0 " not in result,  "FAIL: old lines not trimmed"

    print(f"PASS: {len(big_log)} chars → {len(result)} chars")
    print(f"PASS: {201} lines → {len(result.splitlines())} lines")
    print("PASS: Priority error line preserved")


def test_full_processor():
    print_section("TEST 3: Full Processor Pipeline")
    result = process(MOCK_INCIDENT)

    assert result["incident_id"] == "test-1234",    "FAIL: incident_id wrong"
    assert result["error_type"] == "HIGH_CPU",       "FAIL: error_type wrong"
    assert "10.0.1.45" not in result["processed_logs"], "FAIL: IP not sanitized"
    assert result["log_char_count"] > 0,             "FAIL: no log chars"
    assert result["environment"] == "dev",           "FAIL: wrong environment"

    print("PASS: Incident ID     →", result["incident_id"])
    print("PASS: Error type      →", result["error_type"])
    print("PASS: Alarm name      →", result["alarm_name"])
    print("PASS: Instance ID     →", result["instance_id"])
    print("PASS: Log lines       →", result["log_line_count"])
    print("PASS: Log chars       →", result["log_char_count"])
    print("PASS: Processed at    →", result["processed_at"])
    print("PASS: IPs sanitized   → confirmed")
    print("\nAI-Ready Payload:")
    print(f"  incident_id:   {result['incident_id']}")
    print(f"  error_type:    {result['error_type']}")
    print(f"  alarm_state:   {result['alarm_state']}")
    print(f"  log_lines:     {result['log_line_count']}")
    print(f"  log_chars:     {result['log_char_count']}")


if __name__ == "__main__":
    print("\nAIOps Sentinel — Log Processor Tests")
    passed = failed = 0

    for test in [test_sanitizer, test_trimmer, test_full_processor]:
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

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
