"""
agents/anonymizer.py
─────────────────────
Subagent 1: Privacy Guard & Parser (The Anonymizer)

Responsibility:
  - Input:  raw_payload (messy medical chart text)
  - Output: clean_fhir_json (FHIRPayload) stored in PipelineState

What it does:
  1. Sends the raw chart to Claude with a strict anonymization + FHIR
     extraction system prompt.
  2. Claude returns a JSON string matching the FHIRPayload schema.
  3. We parse and validate with Pydantic before storing.

Architecture note — why not regex-first?
  Clinical notes are notoriously unstructured. Lab values appear in tables,
  prose, and shorthand. A purely regex-based approach misses too much.
  We use Claude to do the heavy lifting of understanding the clinical context,
  then validate its output with Pydantic to guarantee the downstream agents
  receive a well-formed object.

HIPAA compliance:
  - We pass the raw chart ONLY to the Claude Messages API (Anthropic's
    infrastructure, covered under BAA for enterprise).
  - The output FHIRPayload must not contain names, phones, emails, or DOB.
  - A post-parse audit scan from the HIPAA hook is run on the serialized
    output and any findings are logged as warnings.
"""

from __future__ import annotations

import json
import os

import anthropic
from pydantic import ValidationError

from utils.logger import get_logger
from utils.state import FHIRPayload, LabResult, PatientProfile, PipelineState
from hooks.hipaa_guardrail import sanitize_check

logger = get_logger(__name__)

_MODEL: str = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a HIPAA-compliant medical data processor. Your job is to:

1. ANONYMIZE the patient chart by removing all Personally Identifiable Information (PII):
   - Remove: Full names, phone numbers, email addresses, home addresses, SSN
   - Convert: Specific birthdates → age ranges (e.g., "born 1978-03-15" → "45-50 years old")
   - Remove: Specific ZIP codes (replace with region if relevant, e.g., "Northeast US")
   - Keep:   Medical data, lab values, diagnoses, medications

2. EXTRACT and STRUCTURE the anonymized data into the following JSON format EXACTLY:

{
  "patient": {
    "age_range": "<e.g. '45-50 years old'>",
    "gender": "<Male|Female|Non-binary|Unknown>",
    "anonymized": true
  },
  "conditions": ["<primary condition>", "<secondary condition>", ...],
  "medications": ["<drug name> <dose>", ...],
  "lab_results": [
    {
      "test": "<test name>",
      "value": <numeric value or "Positive"/"Negative">,
      "unit": "<unit string, e.g. mg/dL, %, x10^9/L>",
      "reference_range": "<normal range if mentioned>"
    }
  ],
  "prior_treatments": ["<treatment>", ...],
  "contraindications": ["<known allergy or contraindication>", ...]
}

CRITICAL RULES:
- Output ONLY valid JSON. No markdown, no explanation, no preamble.
- If a field has no data, use an empty array [] or empty string "".
- For lab values, ALWAYS include the unit. If the chart shows mg/dL, keep mg/dL.
- If you see abbreviations like "ANC" (Absolute Neutrophil Count), expand them.
- If you see unit shorthand like "K/μL" or "K/uL", normalize to "x10^9/L".
- Convert all lab values to their standard SI units AND note the original unit.
- NEVER include a real person's name, phone number, email, or date of birth.
"""

# ── Agent class ───────────────────────────────────────────────────────────────

class AnonymizerAgent:
    """
    Subagent 1: Strips PII and extracts structured FHIR JSON from raw chart text.

    This agent uses a single Claude call (no tool use needed — pure NL→JSON).
    We use a high max_tokens budget because charts can be verbose and we need
    the full JSON output.
    """

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = _MODEL
        logger.info(f"AnonymizerAgent initialized with model={self.model}")

    def run(self, state: PipelineState) -> PipelineState:
        """
        Execute the anonymization and FHIR extraction pass.

        Args:
            state: Pipeline state containing raw_payload.

        Returns:
            Updated state with clean_fhir_json populated.
        """
        logger.info("─── Subagent 1: Anonymizer started ───")

        if not state.raw_payload:
            state.add_error(
                agent="AnonymizerAgent",
                error_type="EmptyInput",
                message="raw_payload is empty — nothing to anonymize.",
                recoverable=False,
            )
            return state

        try:
            fhir_payload = self._call_claude(state.raw_payload)
            state.clean_fhir_json = fhir_payload

            # Post-parse PII audit (non-blocking — logs warnings only)
            serialized = fhir_payload.model_dump_json()
            findings = sanitize_check(serialized, context="FHIR JSON output")
            if findings:
                logger.warning(
                    f"Anonymizer PII audit found residual patterns: {findings}. "
                    "These may be false positives (e.g., lab value format matching a phone pattern)."
                )

            logger.info(
                f"Anonymizer complete — "
                f"conditions={len(fhir_payload.conditions)}, "
                f"medications={len(fhir_payload.medications)}, "
                f"lab_results={len(fhir_payload.lab_results)}"
            )

        except ValidationError as exc:
            logger.error(f"FHIR JSON validation failed: {exc}")
            state.add_error(
                agent="AnonymizerAgent",
                error_type="ValidationError",
                message=f"Claude returned malformed JSON: {exc}",
                recoverable=False,
            )
        except anthropic.APIError as exc:
            logger.error(f"Anthropic API error in Anonymizer: {exc}")
            state.add_error(
                agent="AnonymizerAgent",
                error_type="APIError",
                message=str(exc),
                recoverable=False,
            )
        except Exception as exc:
            logger.error(f"Unexpected error in Anonymizer: {exc}", exc_info=True)
            state.add_error(
                agent="AnonymizerAgent",
                error_type="UnexpectedError",
                message=str(exc),
                recoverable=False,
            )

        return state

    def _call_claude(self, raw_text: str) -> FHIRPayload:
        """
        Send the raw chart to Claude and parse the returned JSON.

        Returns:
            Validated FHIRPayload instance.

        Raises:
            ValidationError: If the JSON doesn't match FHIRPayload schema.
            json.JSONDecodeError: If Claude's response isn't valid JSON.
        """
        logger.debug("Calling Claude for anonymization + FHIR extraction...")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Here is the raw patient chart. "
                        "Extract and anonymize it into the FHIR JSON format:\n\n"
                        f"```\n{raw_text}\n```"
                    ),
                }
            ],
        )

        raw_json_str: str = response.content[0].text.strip()

        # Claude sometimes wraps JSON in ```json ... ``` fences — strip them
        if raw_json_str.startswith("```"):
            lines = raw_json_str.split("\n")
            raw_json_str = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()

        logger.debug(f"Claude FHIR response length: {len(raw_json_str)} chars")

        parsed: dict = json.loads(raw_json_str)

        # Pydantic validates the shape and coerces types
        fhir_payload = FHIRPayload(
            patient=PatientProfile(**parsed.get("patient", {})),
            conditions=parsed.get("conditions", []),
            medications=parsed.get("medications", []),
            lab_results=[
                LabResult(**lr) for lr in parsed.get("lab_results", [])
            ],
            prior_treatments=parsed.get("prior_treatments", []),
            contraindications=parsed.get("contraindications", []),
        )

        return fhir_payload
