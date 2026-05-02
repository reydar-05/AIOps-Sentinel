"""
Root Cause Analysis prompt template for Groq Llama.
Designed for structured JSON output (response_format: json_object).
"""


def build_rca_prompt(payload: dict) -> str:
    """
    Build a strong, structured prompt for AI-based incident analysis.
    Output is strictly JSON — no prose, no markdown fences.

    Key prompt-engineering choices:
      - Logs are presented BEFORE alarm metadata (anchors AI on logs first).
      - Explicit instruction to QUOTE log content, not paraphrase the alarm.
      - Environment is reiterated in the instructions section to prevent the
        AI from inventing one ("dev"/"prod" hallucination).
      - Confidence is anchored to log clarity, not gut feeling.
    """
    env       = payload.get("environment", "unknown")
    alarm     = payload.get("alarm_name", "N/A")
    state     = payload.get("alarm_state", "N/A")
    reason    = payload.get("alarm_reason", "N/A")
    logs      = payload.get("processed_logs", "[No logs available]")
    error_pre = payload.get("error_type", "UNKNOWN")

    return f"""You are an expert AWS Site Reliability Engineer and AIOps analyst.
Your job is to read the SYSTEM LOGS below and determine what happened.
Do NOT just paraphrase the alarm — the alarm tells you that something fired,
but the LOGS tell you why. Quote specific error keywords, exception names,
status codes, file paths, or stack-trace frames from the logs.

SYSTEM LOGS (sanitised, last 15 minutes — this is the PRIMARY source of truth):
--------------------------------------------------------------------------------
{logs}

ALARM CONTEXT (secondary — use only to confirm what the logs already show):
---------------------------------------------------------------------------
Alarm Name      : {alarm}
Alarm State     : {state}
Alarm Reason    : {reason}
Pre-classified  : {error_pre}
Environment     : {env}        <-- IMPORTANT: use this exact value, do not change it
Incident ID     : {payload.get('incident_id')}
Timestamp       : {payload.get('timestamp')}
Instance ID     : {payload.get('instance_id', 'N/A')}
ASG Name        : {payload.get('asg_name', 'N/A')}
Region          : {payload.get('region')}

INSTRUCTIONS:
-------------
1. PRIMARY TASK: Identify the actual error pattern in the logs above. Mention
   specific keywords from the logs in your "root_cause" and "summary" fields
   (e.g., NullPointerException, KeyError, OOMKilled, 502 Bad Gateway, port
   already in use, connection refused, etc.).
2. Classify severity based on:
     - Environment: {env} (prod >> staging >> dev for severity weighting)
     - User-facing impact (does the log mention customer impact, 5xx, downtime?)
     - Error pattern (FATAL/CRITICAL >> ERROR >> WARN >> INFO)
3. Set "confidence" to:
     - HIGH   — logs contain explicit, unambiguous error keywords
     - MEDIUM — logs partially explain the issue but require some inference
     - LOW    — logs are missing, generic, or do not match the alarm
4. List "affected_components" using AWS service names (EC2, RDS, ElastiCache,
   ALB, Lambda, EKS) plus any application components named in the logs.
5. "immediate_actions" must be 2-4 concrete, runnable steps (commands, API
   calls, console paths) — not vague advice.
6. The "environment" you reference must be exactly: {env}

Respond ONLY with a valid JSON object — no prose, no markdown fences, no
explanation outside the JSON. Use exactly this structure:

{{
  "summary":          "One sentence stating what the LOGS show happened (not what the alarm fired about).",
  "root_cause":       "2-3 sentences. Quote specific error keywords/exception names from the logs.",
  "severity":         "CRITICAL | HIGH | MEDIUM | LOW",
  "severity_reason":  "Why you chose this severity. Reference the environment ({env}) and impact.",
  "affected_components": ["list", "of", "AWS", "services", "and", "app", "components"],
  "immediate_actions": [
    "Concrete action 1 (command, console path, or API call)",
    "Concrete action 2"
  ],
  "long_term_fix":    "Architectural or config change that prevents recurrence.",
  "pattern_detected": true or false,
  "pattern_description": "Describe the pattern if true, otherwise null.",
  "confidence":       "HIGH | MEDIUM | LOW",
  "estimated_impact": "User-facing impact in one sentence."
}}"""
