"""
AIOps Sentinel — offline demo for reviews. No AWS account needed.

Runs the REAL pipeline code (event parser -> log sanitizer -> trimmer ->
classifier -> RCA prompt -> AI -> Discord formatter) on a sample incident
and prints every stage.

  python scripts/demo.py               # canned AI response (fully offline)
  GROQ_API_KEY=gsk_... python scripts/demo.py   # live Llama 3.3 70B analysis
  DISCORD_WEBHOOK_URL=... python scripts/demo.py  # also posts to Discord
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
for sub in ("incident_processor", "log_processor", "ai_analyzer", "notification_handler"):
    sys.path.insert(0, os.path.join(ROOT, "lambda", sub))
sys.path.insert(0, os.path.join(ROOT, "ai", "prompts"))
os.environ.setdefault("AWS_REGION", "ap-south-1")
os.environ.setdefault("LOG_LEVEL", "ERROR")

from event_parser import parse_event
from processor import process
from rca_prompt import build_rca_prompt
from discord_formatter import format_alert
import notifier

RAW_LOGS = "\n".join([
    "[2026-01-15T10:28:00Z] INFO  Server started on 10.0.1.25:8080",
    "[2026-01-15T10:28:30Z] INFO  db connect user=admin password=S3cret! host=ip-10-0-1-99.ap-south-1.compute.internal",
    "[2026-01-15T10:29:00Z] ERROR java.lang.OutOfMemoryError: Java heap space (owner: ops@example.com)",
    "[2026-01-15T10:29:01Z] ERROR   at com.app.DataProcessor.process(DataProcessor.java:142)",
    "[2026-01-15T10:29:30Z] FATAL Process killed by OOM killer",
    "[2026-01-15T10:30:00Z] CRITICAL CPU utilization 92.5% for 2 periods",
])

CANNED_AI = {
    "summary": "Java heap exhaustion (OutOfMemoryError) in DataProcessor led to the process being OOM-killed.",
    "root_cause": "Logs show java.lang.OutOfMemoryError: Java heap space at DataProcessor.java:142, "
                  "followed by 'Process killed by OOM killer'. GC thrashing drove CPU above 90%.",
    "severity": "HIGH", "severity_reason": "Service process killed; dev environment.",
    "affected_components": ["EC2", "Java application", "DataProcessor"],
    "immediate_actions": ["sudo systemctl restart app.service",
                          "Raise JVM heap: JAVA_OPTS=-Xmx2g",
                          "aws autoscaling set-desired-capacity --auto-scaling-group-name aiops-asg-dev --desired-capacity 3"],
    "long_term_fix": "Fix the memory leak in DataProcessor.process and add a heap-usage alarm.",
    "pattern_detected": False, "pattern_description": None, "confidence": "HIGH",
    "estimated_impact": "Application unavailable until restarted.",
}


def banner(n, title):
    print(f"\n{'=' * 70}\n  STAGE {n}: {title}\n{'=' * 70}")


def main():
    with open(os.path.join(ROOT, "tests", "fixtures", "lambda_test_event.json")) as f:
        event = json.load(f)

    banner(1, "Parse SNS event -> normalized incident")
    incident = parse_event(event)
    print(json.dumps({k: incident[k] for k in ("incident_id", "event_type", "alarm_name", "new_state", "reason")}, indent=2))

    banner(2, "Raw logs (contain secrets!)")
    print(RAW_LOGS)
    incident["raw_logs"] = RAW_LOGS

    banner(3, "Sanitize + trim + classify")
    payload = process(incident)
    print(payload["processed_logs"])
    print(f"\nerror_type = {payload['error_type']} | {payload['log_char_count']} chars")

    banner(4, "AI root-cause analysis")
    if os.environ.get("GROQ_API_KEY"):
        from analyzer import analyze
        print("Calling Groq (Llama 3.3 70B) ...")
        enriched = analyze(payload)
    else:
        print("GROQ_API_KEY not set -> using canned AI response (prompt below is what would be sent)\n")
        print(build_rca_prompt(payload)[:900] + "\n  [...]")
        enriched = {**payload, "ai_analysis": CANNED_AI}
    print(json.dumps(enriched["ai_analysis"], indent=2))

    banner(5, "Discord alert")
    message = format_alert(enriched)
    embed = message["embeds"][0]
    print(embed["title"], "\n", embed["description"], sep="")
    for fld in embed["fields"]:
        print(f"  [{fld['name']}] {fld['value']}")
    if os.environ.get("DISCORD_WEBHOOK_URL"):
        print("\nPosting to Discord ->", "sent" if notifier.send_alert(enriched) else "FAILED")
    else:
        print("\n(DISCORD_WEBHOOK_URL not set - not posted)")


if __name__ == "__main__":
    main()
