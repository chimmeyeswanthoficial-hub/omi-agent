"""Redact provider-looking secrets before transcripts/logs hit disk or UI."""

from __future__ import annotations

import re

_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),  # openai / litellm / openrouter style
    re.compile(r"gsk_[A-Za-z0-9]{16,}"),  # groq
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),  # google
    re.compile(r"deepseek-[A-Za-z0-9]{16,}"),  # deepseek
    re.compile(r"(?i)(api[_-]?key|authorization)\s*[:=]\s*\S+"),
]


def redact_text(text: str) -> str:
    for pat in _PATTERNS:
        text = pat.sub("***REDACTED***", text)
    return text
