"""
Root Cause Analysis prompt template for Amazon Bedrock.
Designed for Claude 3.5 Sonnet — structured JSON output.
"""


def build_rca_prompt(payload: dict) -> str:
    """
    Build a strong, structured prompt for AI-based incident analysis.
    Output is strictly JSON — no prose, no markdown fences.
    """
    return f"""You are an expert AWS Site Reliability Engineer and AIOps analyst.
Analyze the following infrastructure incident and provide a structured diagnosis.

INCIDENT DETAILS:
-----------------
Incident ID   : {payload.get('incident_id')}
Timestamp     : {payload.get('timestamp')}
Event Type    : {payload.get('event_type')}
Alarm Name    : {payload.get('alarm_name')}
Alarm State   : {payload.get('alarm_state')}
Alarm Reason  : {payload.get('alarm_reason')}
Instance ID   : {payload.get('instance_id', 'N/A')}
ASG Name      : {payload.get('asg_name', 'N/A')}
Region        : {payload.get('region')}
Pre-classified: {payload.get('error_type')}
Environment   : {payload.get('environment')}

SYSTEM LOGS (sanitized, last 15 minutes):
------------------------------------------
{payload.get('processed_logs', '[No logs available]')}

INSTRUCTIONS:
-------------
1. Analyze the alarm reason and logs carefully.
2. Identify the most likely root cause.
3. Classify severity based on business impact.
4. Suggest immediate and long-term fixes.
5. Identify if this could indicate a wider pattern.

Respond ONLY with a valid JSON object. No explanation outside the JSON.
Use exactly this structure:

{{
  "summary": "One sentence describing what happened",
  "root_cause": "Technical explanation of the underlying cause (2-3 sentences)",
  "severity": "CRITICAL | HIGH | MEDIUM | LOW",
  "severity_reason": "Why you chose this severity level",
  "affected_components": ["list", "of", "affected", "AWS", "services"],
  "immediate_actions": [
    "Action 1 to take right now",
    "Action 2 to take right now"
  ],
  "long_term_fix": "What architectural or config change prevents recurrence",
  "pattern_detected": true or false,
  "pattern_description": "If true, describe the pattern. If false, write null",
  "confidence": "HIGH | MEDIUM | LOW",
  "estimated_impact": "User-facing impact description"
}}"""
