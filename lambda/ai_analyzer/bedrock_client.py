"""
Amazon Bedrock client — invokes Claude 3.5 Sonnet for RCA.
Handles retries, token limits, and response parsing.
"""

import boto3
import json
import logging
import os
import time

logger = logging.getLogger(__name__)

# ── Bedrock client ─────────────────────────────────────────────────
bedrock = boto3.client(
    "bedrock-runtime",
    region_name=os.environ.get("AWS_REGION", "ap-south-1")
)

MODEL_ID    = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
MAX_TOKENS  = int(os.environ.get("BEDROCK_MAX_TOKENS", "2048"))
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Detect model family for correct request format
def _is_anthropic(model_id: str) -> bool:
    return "anthropic" in model_id.lower()


def invoke(prompt: str) -> dict:
    """
    Send prompt to Bedrock and return parsed JSON response.
    Supports both Anthropic Claude and Amazon Nova model formats.
    Retries up to MAX_RETRIES times on transient errors.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("Bedrock invoke attempt %d/%d | model: %s",
                        attempt, MAX_RETRIES, MODEL_ID)

            if _is_anthropic(MODEL_ID):
                # Anthropic Claude format
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": MAX_TOKENS,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "top_p": 0.9
                })
            else:
                # Amazon Nova / Titan format
                body = json.dumps({
                    "messages": [{"role": "user", "content": [{"text": prompt}]}],
                    "inferenceConfig": {
                        "max_new_tokens": MAX_TOKENS,
                        "temperature": 0.1,
                        "top_p": 0.9
                    }
                })

            response = bedrock.invoke_model(
                modelId=MODEL_ID,
                body=body,
                contentType="application/json",
                accept="application/json"
            )

            response_body = json.loads(response["body"].read())

            # Parse response based on model family
            if _is_anthropic(MODEL_ID):
                raw_text = response_body["content"][0]["text"].strip()
            else:
                # Amazon Nova response format
                raw_text = response_body["output"]["message"]["content"][0]["text"].strip()

            logger.info("Bedrock response received — %d chars", len(raw_text))

            # ── Parse JSON from response ───────────────────────────
            analysis = _parse_response(raw_text)
            return analysis

        except bedrock.exceptions.ThrottlingException:
            wait = RETRY_DELAY * attempt
            logger.warning("Bedrock throttled — waiting %ds before retry", wait)
            time.sleep(wait)

        except bedrock.exceptions.ModelErrorException as e:
            logger.error("Bedrock model error: %s", str(e))
            raise

        except Exception as e:
            if attempt == MAX_RETRIES:
                logger.error("Bedrock invoke failed after %d attempts: %s",
                             MAX_RETRIES, str(e))
                raise
            logger.warning("Attempt %d failed: %s — retrying", attempt, str(e))
            time.sleep(RETRY_DELAY)

    raise RuntimeError("Bedrock invoke failed after all retries")


def _parse_response(raw_text: str) -> dict:
    """
    Extract and validate JSON from Bedrock response.
    Handles cases where model wraps JSON in markdown fences.
    """
    # Strip markdown fences if present
    if "```json" in raw_text:
        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_text:
        raw_text = raw_text.split("```")[1].split("```")[0].strip()

    try:
        analysis = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Bedrock JSON response: %s", str(e))
        logger.error("Raw response: %s", raw_text[:500])
        # Return a safe fallback rather than crashing
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

    # ── Validate required fields ───────────────────────────────────
    required = ["summary", "root_cause", "severity", "immediate_actions"]
    for field in required:
        if field not in analysis:
            logger.warning("Missing field in AI response: %s", field)
            analysis[field] = "Not provided"

    # ── Normalize severity to valid values ─────────────────────────
    valid_severities = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
    if analysis.get("severity", "").upper() not in valid_severities:
        analysis["severity"] = "HIGH"

    analysis["severity"] = analysis["severity"].upper()

    return analysis
