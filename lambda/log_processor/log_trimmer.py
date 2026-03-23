"""
Log Trimmer — trims logs to stay within Bedrock token limits.
Claude has a context window but we keep prompts lean for cost + speed.

Strategy:
  - Keep LAST N lines (most recent = most relevant)
  - Hard cap on characters
  - Preserve error/critical lines even if old
"""

import logging
import re

logger = logging.getLogger(__name__)

MAX_CHARS = 4000          # ~1000 tokens — leaves room for prompt + response
MAX_LINES = 50            # Max log lines to send
PRIORITY_KEYWORDS = [     # Always keep lines with these keywords
    "error", "critical", "fatal", "exception",
    "traceback", "killed", "oom", "segfault",
    "timeout", "connection refused", "disk full"
]


def trim(log_text: str) -> str:
    """
    Trim logs intelligently:
    1. Extract priority (error) lines
    2. Take last N lines of remaining logs
    3. Combine and cap at MAX_CHARS
    """
    # Placeholder messages start with [No / [Log / [Error — not timestamps
    if not log_text or (log_text.startswith("[") and "]" not in log_text[:40]):
        return log_text  # Return placeholder as-is

    lines = log_text.splitlines()
    original_count = len(lines)

    # ── 1. Separate priority lines ─────────────────────────────────
    priority_lines = []
    normal_lines = []

    for line in lines:
        if any(kw in line.lower() for kw in PRIORITY_KEYWORDS):
            priority_lines.append(line)
        else:
            normal_lines.append(line)

    # ── 2. Take last N normal lines (most recent) ──────────────────
    keep = max(1, MAX_LINES - len(priority_lines))
    normal_lines = normal_lines[-keep:]

    # ── 3. Truncate normal lines by chars (priority lines always kept) ──
    normal_text = "\n".join(normal_lines)
    if len(normal_text) > MAX_CHARS:
        normal_text = normal_text[-MAX_CHARS:]
        normal_text = f"[...truncated to last {MAX_CHARS} chars...]\n" + normal_text

    # ── 4. Priority lines always go at the TOP ─────────────────────
    priority_text = "\n".join(priority_lines)
    if priority_text and normal_text:
        result = priority_text + "\n" + normal_text
    elif priority_text:
        result = priority_text
    else:
        result = normal_text

    logger.info("Log trimmer: %d lines → %d chars",
                original_count, len(result))

    return result
