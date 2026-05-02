"""
AI Analyzer — orchestrates Groq RCA for an incident payload.
"""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../ai/prompts"))

from rca_prompt import build_rca_prompt
import groq_client

logger = logging.getLogger(__name__)


def analyze(payload: dict) -> dict:
    """
    Run AI root cause analysis on a processed incident payload.
    Uses Groq (Llama 3.3 70B). Returns enriched payload with AI analysis fields.
    """
    logger.info("Starting AI analysis for incident: %s", payload.get("incident_id"))

    prompt = build_rca_prompt(payload)
    logger.debug("Prompt length: %d chars", len(prompt))

    analysis = groq_client.invoke(prompt)
    logger.info("AI analysis via Groq complete")

    enriched = {**payload, "ai_analysis": analysis}

    logger.info(
        "AI analysis complete | severity: %s | confidence: %s",
        analysis.get("severity"),
        analysis.get("confidence"),
    )

    return enriched
