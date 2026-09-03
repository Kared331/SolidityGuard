"""
Input sanitizer for LLM audit pipeline.
Detects and mitigates prompt injection attempts.
"""

import re

# Known prompt injection patterns
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)\s+instructions?",
    r"you\s+are\s+(now|no\s+longer)\s+a\s+",
    r"forget\s+(all\s+)?(previous|prior)\s+",
    r"system\s*:\s*",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"\[INST\]",
    r"\[/INST\]",
    r"DAN\s+mode",
    r"jailbreak",
]


class InputSanitizer:
    """Sanitizes user-provided Solidity code before sending to LLM."""

    MAX_CODE_LENGTH = 32000  # characters

    @staticmethod
    def sanitize_code(code: str) -> tuple[str, bool]:
        """Sanitize code and detect injection. Returns (cleaned_code, injection_detected)."""
        # Remove null bytes and non-printable chars (except newlines)
        sanitized = code.replace("\x00", "")
        sanitized = re.sub(r"[^\x20-\x7E\n\t\r]", "", sanitized)

        # Truncate to max length
        if len(sanitized) > InputSanitizer.MAX_CODE_LENGTH:
            sanitized = sanitized[: InputSanitizer.MAX_CODE_LENGTH] + "\n// ... (truncated)"

        # Detect injection
        injection_detected = bool(InputSanitizer.detect_injection(sanitized))
        return sanitized, injection_detected

    @staticmethod
    def detect_injection(text: str) -> list[str]:
        """Detect prompt injection patterns. Returns list of matched patterns."""
        detected = []
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(pattern)
        return detected

    @staticmethod
    def sanitize(text: str) -> tuple[str, list[str]]:
        """Full sanitization: clean code + detect injection. Returns (cleaned, warnings)."""
        cleaned, _ = InputSanitizer.sanitize_code(text)
        warnings = InputSanitizer.detect_injection(cleaned)
        return cleaned, warnings


input_sanitizer = InputSanitizer()
