"""
Real-world log AI quality gate. Calls the live Groq API; skips (exit 0)
when GROQ_API_KEY is not set so CI stays green on forks / without secrets.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lambda/ai_analyzer"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ai/prompts"))

SCENARIOS = [
    ("OOM", "ERROR java.lang.OutOfMemoryError: Java heap space\nFATAL Process killed", "outofmemory"),
    ("DISK", "ERROR write failed: No space left on device /var/log", "space"),
    ("DB", "ERROR connection refused to postgres:5432\nERROR timeout after 30s", "connection"),
]


def test_real_world_logs():
    if not os.environ.get("GROQ_API_KEY"):
        print("SKIP: GROQ_API_KEY not set")
        return
    from analyzer import analyze
    passed = 0
    for name, logs, keyword in SCENARIOS:
        out = analyze({"incident_id": name, "environment": "dev", "alarm_name": "test",
                       "alarm_state": "ALARM", "alarm_reason": "test", "processed_logs": logs,
                       "error_type": "UNKNOWN", "region": "ap-south-1"})["ai_analysis"]
        text = (out.get("summary", "") + out.get("root_cause", "")).lower().replace(" ", "")
        ok = keyword in text
        print(f"{'PASS' if ok else 'FAIL'}: {name}")
        passed += ok
    assert passed >= 1, "AI mentioned no expected keywords in any scenario"


if __name__ == "__main__":
    test_real_world_logs()
