"""
OpenRouter AI client — fallback AI for RCA when Bedrock is unavailable.
Uses OpenRouter free tier (Llama 3.1) — no card needed, works from Lambda.
"""

import json
import logging
import os
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS  = [
    "google/gemma-3n-e4b-it:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "openai/gpt-oss-20b:free",
    "qwen/qwen3-4b:free",
    "z-ai/glm-4.5-air:free",
]
MAX_TOKENS         = int(os.environ.get("BEDROCK_MAX_TOKENS", "2048"))


def invoke(prompt: str) -> dict:
    """
    Send prompt to OpenRouter and return parsed JSON analysis.
    Uses urllib (built-in) — no extra dependencies.
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY (OpenRouter key) not set")

    last_error = None
    for model in OPENROUTER_MODELS:
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": MAX_TOKENS,
            "temperature": 0.1,
        }).encode("utf-8")

        req = urllib.request.Request(
            OPENROUTER_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/reydar-05/aiops-sentinel",
                "X-Title": "AIOps Sentinel"
            },
            method="POST"
        )

        logger.info("OpenRouter invoke | model: %s", model)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            raw_text = body["choices"][0]["message"]["content"].strip()
            logger.info("OpenRouter response received — %d chars via %s", len(raw_text), model)
            return _parse_response(raw_text)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.warning("OpenRouter model %s failed (%d) — trying next", model, e.code)
            last_error = RuntimeError(f"OpenRouter API error {e.code}: {error_body}")

    raise last_error or RuntimeError("All OpenRouter models failed")


def _parse_response(raw_text: str) -> dict:
    """Extract and validate JSON from OpenRouter response."""
    if "```json" in raw_text:
        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_text:
        raw_text = raw_text.split("```")[1].split("```")[0].strip()

    try:
        analysis = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse OpenRouter JSON: %s | raw: %s", str(e), raw_text[:300])
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
            "estimated_impact": "Unknown — manual review needed"
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
