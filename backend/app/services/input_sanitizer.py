"""Input sanitizer for Solidity code before LLM prompts (Sprint 2).

Provides prompt injection detection, token-aware truncation, and
non-printable character removal as described in blueprint 7.1.
"""

import re
from typing import Tuple


class InputSanitizer:
    """Comprehensive input sanitization for Solidity code."""

    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"you\s+are\s+now\s+",
        r"forget\s+(all\s+)?previous",
        r"new\s+instructions:",
        r"system\s*:\s*",
        r"assistant\s*:\s*",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
    ]

    # Token-aware truncation: ~8000 tokens * 4 chars/token
    _MAX_CHARS = 32000

    @classmethod
    def sanitize_code(cls, code: str) -> Tuple[str, bool]:
        """Sanitize Solidity code and detect injection attempts.

        Returns:
            (sanitized_code, injection_detected)
        """
        injection_detected = False

        # Check for injection patterns
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                injection_detected = True
                code = re.sub(pattern, "[REDACTED]", code, flags=re.IGNORECASE)

        # Token-aware truncation (approx 4 chars per token)
        if len(code) > cls._MAX_CHARS:
            code = code[: cls._MAX_CHARS] + "\n// ... truncated ..."

        # Remove non-printable characters (except newlines/tabs)
        code = re.sub(r"[^\x20-\x7e\n\t\r]", "", code)

        return code, injection_detected