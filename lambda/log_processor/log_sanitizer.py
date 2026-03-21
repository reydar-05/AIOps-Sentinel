"""
Log Sanitizer — removes sensitive data before sending to AI.
Strips: IPs, AWS credentials, internal paths, tokens, emails.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── Regex patterns for sensitive data ─────────────────────────────
PATTERNS = [
    # IPv4 addresses
    (re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'), "[IP_REDACTED]"),

    # AWS Access Key IDs
    (re.compile(r'\bAKIA[0-9A-Z]{16}\b'), "[AWS_KEY_REDACTED]"),

    # AWS Secret Keys (40 char alphanumeric)
    (re.compile(r'(?<![A-Z0-9])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])'), "[AWS_SECRET_REDACTED]"),

    # Generic tokens/passwords in key=value format
    (re.compile(r'(?i)(password|token|secret|key|auth|credential)\s*[=:]\s*\S+'), "[CREDENTIAL_REDACTED]"),

    # Email addresses
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), "[EMAIL_REDACTED]"),

    # Internal AWS VPC DNS names
    (re.compile(r'\bip-\d{1,3}-\d{1,3}-\d{1,3}-\d{1,3}\..*?\.internal\b'), "[INTERNAL_HOST_REDACTED]"),

    # File paths with usernames
    (re.compile(r'/home/[a-zA-Z0-9_-]+/'), "/home/[USER]/"),
    (re.compile(r'/Users/[a-zA-Z0-9_-]+/'), "/Users/[USER]/"),
]


def sanitize(log_text: str) -> str:
    """Apply all redaction patterns to log text."""
    if not log_text:
        return log_text

    original_length = len(log_text)
    sanitized = log_text

    for pattern, replacement in PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    redacted_count = log_text.count("\n") - sanitized.count("\n")
    logger.debug("Sanitized logs: %d → %d chars", original_length, len(sanitized))

    return sanitized
