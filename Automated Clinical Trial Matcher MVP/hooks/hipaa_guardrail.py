"""
hooks/hipaa_guardrail.py
────────────────────────
PreToolUse HIPAA guardrail — aborts any outbound tool call that contains
unredacted Personally Identifiable Information (PII).

Architecture note:
    In the Claude Agent SDK, hooks intercept the agentic loop before a tool
    is actually executed. This hook is registered with the orchestrator and
    called by every agent that performs an external network request (i.e.,
    the Searcher's `search_clinical_trials` tool).

    If PII is found → raises HIPAAViolationError (caught by orchestrator).
    If clean       → returns True (execution proceeds).

PII patterns we detect:
    - Full names        (Title + CapWord CapWord)
    - US phone numbers  (various formats)
    - Email addresses
    - US SSN
    - Specific 5-digit ZIP codes that appear verbatim in the payload
      (a ZIP by itself isn't PII, but combined with a name it narrows
      re-identification — we flag them conservatively)
    - ISO date of birth that maps to a specific person (YYYY-MM-DD)

Design decision: We err on the side of false positives (blocking a clean
payload) rather than false negatives (leaking PII). If a false positive
occurs, the Anonymizer should be re-prompted to clean more aggressively.
"""

from __future__ import annotations

import json
import re
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)


# ── Custom exception ──────────────────────────────────────────────────────────

class HIPAAViolationError(Exception):
    """
    Raised when the PreToolUse hook detects PII in an outbound payload.

    Attributes:
        tool_name:  Name of the tool that was about to be called.
        pii_type:   Human-readable description of what was found.
        detail:     The matched string (truncated for safety in logs).
    """
    def __init__(self, tool_name: str, pii_type: str, detail: str) -> None:
        self.tool_name = tool_name
        self.pii_type = pii_type
        self.detail = detail
        super().__init__(
            f"[HIPAA BLOCK] Tool '{tool_name}' aborted — {pii_type} detected "
            f"in outbound payload. Detail: '{detail[:40]}...'"
        )


# ── PII detection patterns ────────────────────────────────────────────────────

_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "Full name (Title + Name)",
        re.compile(
            r"\b(Mr|Mrs|Ms|Dr|Prof|Miss)\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Full name (First + Last, CapCase)",
        re.compile(r"\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b"),
    ),
    (
        "US phone number",
        re.compile(
            r"(\+?1[\s\-.]?)?"           # optional country code
            r"\(?\d{3}\)?[\s\-.]"        # area code
            r"\d{3}[\s\-.]"              # exchange
            r"\d{4}\b"                   # subscriber
        ),
    ),
    (
        "Email address",
        re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
    ),
    (
        "US Social Security Number",
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    ),
    (
        "Specific date of birth (YYYY-MM-DD or MM/DD/YYYY)",
        re.compile(
            r"\b(19|20)\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b"  # ISO
            r"|"
            r"\b(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/(19|20)\d{2}\b"  # US
        ),
    ),
    (
        "5-digit ZIP code (standalone)",
        re.compile(r"\b\d{5}(-\d{4})?\b"),
    ),
]


# ── Hook implementation ───────────────────────────────────────────────────────

def pre_tool_use_hook(tool_name: str, tool_input: dict[str, Any]) -> bool:
    """
    PreToolUse hook — scan the outbound tool payload for PII.

    This function should be called BEFORE executing any tool that makes
    an external network request (e.g., search_clinical_trials).

    Args:
        tool_name:  The name of the tool about to be called.
        tool_input: The dict of arguments the agent prepared for the tool.

    Returns:
        True if the payload is clean and execution should proceed.

    Raises:
        HIPAAViolationError: Immediately if any PII pattern matches.

    Usage in agent loop:
        pre_tool_use_hook("search_clinical_trials", {"condition": "diabetes"})
    """
    # Serialize the entire payload to a single string for scanning.
    # We use ensure_ascii=False so unicode medical terms are preserved as-is
    # rather than being escaped (which could mask patterns).
    payload_str: str = json.dumps(tool_input, ensure_ascii=False)

    logger.debug(f"PreToolUse hook scanning payload for tool '{tool_name}' "
                 f"({len(payload_str)} chars)")

    for pii_type, pattern in _PII_PATTERNS:
        match = pattern.search(payload_str)
        if match:
            matched_text = match.group(0)
            logger.error(
                f"HIPAA VIOLATION: {pii_type} detected in '{tool_name}' payload. "
                f"Matched: '{matched_text[:40]}'"
            )
            raise HIPAAViolationError(
                tool_name=tool_name,
                pii_type=pii_type,
                detail=matched_text,
            )

    logger.debug(f"PreToolUse hook PASSED for tool '{tool_name}' — no PII detected")
    return True


def sanitize_check(text: str, context: str = "unknown") -> list[str]:
    """
    Non-blocking PII scan that returns a list of findings (for audit logging).

    Use this for post-hoc auditing, not as a gate. The gate is pre_tool_use_hook.

    Args:
        text:    The string to scan.
        context: Human-readable label for logging (e.g., "FHIR JSON output").

    Returns:
        List of human-readable PII findings, empty if clean.
    """
    findings: list[str] = []
    for pii_type, pattern in _PII_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            findings.append(f"{pii_type}: {len(matches)} occurrence(s)")

    if findings:
        logger.warning(f"PII audit [{context}] — found: {findings}")
    else:
        logger.debug(f"PII audit [{context}] — clean")

    return findings
