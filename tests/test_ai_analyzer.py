"""
Local test for AI Analyzer — calls real Groq API.
Requires GROQ_API_KEY environment variable to be set
(get a free key at https://console.groq.com/keys).

Usage:
    python tests/test_ai_analyzer.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lambda/ai_analyzer"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ai/prompts"))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

os.environ["AWS_REGION"]      = "ap-south-1"
os.environ["ENVIRONMENT"]     = "dev"
os.environ.setdefault("GROQ_MAX_TOKENS", "2048")

from rca_prompt import build_rca_prompt
from analyzer import analyze


# ── Mock processed payload (output of log_processor) ───────────────
MOCK_PAYLOAD = {
    "incident_id":    "test-groq-001",
    "timestamp":      "2024-01-15T10:30:00Z",
    "instance_id":    "i-0abc123def456789",
    "asg_name":       "aiops-asg-dev",
    "region":         "ap-south-1",
    "account_id":     "652197206400",
    "event_type":     "CLOUDWATCH_ALARM",
    "alarm_name":     "aiops-high-cpu-dev",
    "alarm_state":    "ALARM",
    "alarm_reason":   "Threshold Crossed: 2 datapoints [92.5, 88.3] >= 80%",
    "error_type":     "HIGH_CPU",
    "environment":    "dev",
    "processed_logs": """[2024-01-15T10:28:00Z] INFO  Starting application server
[2024-01-15T10:28:30Z] INFO  Connected to DB at [IP_REDACTED]:5432
[2024-01-15T10:29:00Z] ERROR Exception: java.lang.OutOfMemoryError: Java heap space
[2024-01-15T10:29:01Z] ERROR   at com.app.service.DataProcessor.process(DataProcessor.java:142)
[2024-01-15T10:29:10Z] ERROR Connection refused to [IP_REDACTED]:6379 (Redis)
[2024-01-15T10:29:30Z] FATAL Process killed: Out Of Memory
[2024-01-15T10:29:45Z] ERROR Disk usage at 98% on /dev/xvda1
[2024-01-15T10:30:00Z] CRITICAL CPU utilization: 92.5%""",
    "log_char_count": 742,
    "log_line_count": 8,
}


def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_prompt_builder():
    print_section("TEST 1: Prompt Builder (no API call)")
    prompt = build_rca_prompt(MOCK_PAYLOAD)

    assert "incident_id" in prompt.lower() or "test-groq-001" in prompt
    assert "HIGH_CPU" in prompt
    assert "92.5" in prompt
    assert "OutOfMemoryError" in prompt

    print(f"PASS: Prompt built — {len(prompt)} chars")
    print(f"PASS: Contains incident context")
    print(f"PASS: Contains log data")
    print("\nPrompt preview (first 300 chars):")
    print(prompt[:300])


def test_groq_rca():
    print_section("TEST 2: Groq RCA (real API call)")
    if not os.environ.get("GROQ_API_KEY"):
        print("SKIP: GROQ_API_KEY not set — set it to run this test")
        print("      Get a free key at https://console.groq.com/keys")
        return

    print("Calling Groq Llama 3.3 70B...")
    print("This usually takes under 2 seconds...\n")

    result = analyze(MOCK_PAYLOAD)
    analysis = result.get("ai_analysis", {})

    # ── Validate structure ─────────────────────────────────────────
    assert "ai_analysis" in result,                    "FAIL: no ai_analysis key"
    assert "summary" in analysis,                      "FAIL: no summary"
    assert "root_cause" in analysis,                   "FAIL: no root_cause"
    assert analysis.get("severity") in ["CRITICAL", "HIGH", "MEDIUM", "LOW"], \
                                                       "FAIL: invalid severity"
    assert "immediate_actions" in analysis,            "FAIL: no immediate_actions"
    assert isinstance(analysis["immediate_actions"], list), \
                                                       "FAIL: actions not a list"
    assert len(analysis["immediate_actions"]) > 0,     "FAIL: empty actions"

    # ── Print full AI response ─────────────────────────────────────
    print("PASS: AI response received and validated\n")
    print("=" * 60)
    print("  AI ANALYSIS RESULT")
    print("=" * 60)
    print(f"\nSummary:\n  {analysis.get('summary')}")
    print(f"\nRoot Cause:\n  {analysis.get('root_cause')}")
    print(f"\nSeverity:   {analysis.get('severity')}")
    print(f"Reason:     {analysis.get('severity_reason')}")
    print(f"Confidence: {analysis.get('confidence')}")
    print(f"\nAffected Components:")
    for c in analysis.get("affected_components", []):
        print(f"  - {c}")
    print(f"\nImmediate Actions:")
    for i, action in enumerate(analysis.get("immediate_actions", []), 1):
        print(f"  {i}. {action}")
    print(f"\nLong-term Fix:\n  {analysis.get('long_term_fix')}")
    print(f"\nPattern Detected: {analysis.get('pattern_detected')}")
    if analysis.get("pattern_detected"):
        print(f"Pattern:  {analysis.get('pattern_description')}")
    print(f"\nEstimated Impact:\n  {analysis.get('estimated_impact')}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("\nAIOps Sentinel — AI Analyzer Tests")
    passed = failed = 0

    for test in [test_prompt_builder, test_groq_rca]:
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
