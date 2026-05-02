"""
Groq AI client — primary AI engine for RCA.
Uses the Groq API (https://console.groq.com) — fast, free tier, no payment required.
"""

import json
import logging
import os
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Models tried in order. Llama 3.3 70B is the strongest free model on Groq
# and follows JSON instructions reliably; the 8B is a fast fallback.
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

MAX_TOKENS = int(os.environ.get("GROQ_MAX_TOKENS", "2048"))

# Soft daily token ceiling. The free tier on Groq is generous (~14,400 req/day
# on Llama 3.3 70B) but tokens-per-day is the harder limit. When this counter
# is exceeded the client emits a WARN log line — production should configure
# CloudWatch metric filters to alarm on these warnings.
DAILY_TOKEN_LIMIT = int(os.environ.get("GROQ_DAILY_TOKEN_LIMIT", "100000"))

# In-memory counter — resets when the Lambda container is recycled (~hourly).
# Good enough for soft-cost alerting; for a hard ceiling persist this in
# DynamoDB or use Groq's own dashboard quotas.
_tokens_used_today = 0


def invoke(prompt: str) -> dict:
    """
    Send prompt to Groq and return parsed JSON analysis.
    Tries each model in GROQ_MODELS until one succeeds.
    Uses urllib (built-in) — no extra dependencies.
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")

    last_error = None
    for model in GROQ_MODELS:
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": MAX_TOKENS,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")

        req = urllib.request.Request(
            GROQ_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "AIOps-Sentinel/1.0",
                "Accept": "application/json",
            },
            method="POST",
        )

        logger.info("Groq invoke | model: %s", model)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            content = (body.get("choices") or [{}])[0].get("message", {}).get("content")
            if not content:
                logger.warning("Groq model %s returned empty content — trying next", model)
                last_error = RuntimeError(f"Empty response from {model}")
                continue
            _track_usage(model, body.get("usage", {}))
            raw_text = content.strip()
            logger.info("Groq response received — %d chars via %s", len(raw_text), model)
            return _parse_response(raw_text)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.warning("Groq model %s failed (%d) — trying next | %s", model, e.code, error_body[:200])
            last_error = RuntimeError(f"Groq API error {e.code}: {error_body}")
        except urllib.error.URLError as e:
            logger.warning("Groq model %s timed out or unreachable (%s) — trying next", model, e.reason)
            last_error = RuntimeError(f"Groq URLError: {e.reason}")

    raise last_error or RuntimeError("All Groq models failed")


def _track_usage(model: str, usage: dict) -> None:
    """
    Record token usage for the most recent Groq call and emit a WARN
    if cumulative usage exceeds the configured daily ceiling.

    Groq returns OpenAI-compatible usage:
        {"prompt_tokens": N, "completion_tokens": M, "total_tokens": N+M}
    """
    global _tokens_used_today
    total = int(usage.get("total_tokens", 0))
    if total <= 0:
        return

    _tokens_used_today += total
    logger.info(
        "Groq tokens | model=%s prompt=%d completion=%d total=%d | running=%d/%d",
        model,
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
        total,
        _tokens_used_today,
        DAILY_TOKEN_LIMIT,
    )

    if _tokens_used_today > DAILY_TOKEN_LIMIT:
        logger.warning(
            "GROQ COST CEILING EXCEEDED — used %d tokens, limit %d. "
            "Subsequent calls will still be made but should be alarmed on.",
            _tokens_used_today,
            DAILY_TOKEN_LIMIT,
        )


def get_usage_summary() -> dict:
    """Expose the current token counter for tests and dashboards."""
    return {
        "tokens_used_in_container": _tokens_used_today,
        "daily_limit": DAILY_TOKEN_LIMIT,
        "headroom": max(0, DAILY_TOKEN_LIMIT - _tokens_used_today),
    }


def _parse_response(raw_text: str) -> dict:
    """Extract and validate JSON from Groq response."""
    if "```json" in raw_text:
        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_text:
        raw_text = raw_text.split("```")[1].split("```")[0].strip()

    try:
        analysis = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Groq JSON: %s | raw: %s", str(e), raw_text[:300])
        return {
            "summary": "AI analysis failed — manual review required",
            "root_cause": raw_text[:500],
            "severity": "HIGH",
            "severity_reason": "Defaulted to HIGH due to parse failure",
            "affected_components": ["unknown"],
            "immediate_actions": ["Review logs manually", "Check CloudWatch"],
            "long_term_fix": "Investigate AI response parsing",
            "pattern_detected": False,
            "pattern_description": None,
            "confidence": "LOW",
            "estimated_impact": "Unknown — manual review needed",
        }

    required = ["summary", "root_cause", "severity", "immediate_actions"]
    for field in required:
        if field not in analysis:
            analysis[field] = "Not provided"

    valid_severities = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
    if analysis.get("severity", "").upper() not in valid_severities:
        analysis["severity"] = "HIGH"
    analysis["severity"] = analysis["severity"].upper()

    return analysis
