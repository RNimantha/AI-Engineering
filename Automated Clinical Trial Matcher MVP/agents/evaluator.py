"""
agents/evaluator.py
────────────────────
Subagent 3: Eligibility Match Judge (The Critic)

Responsibility:
  - Input:  clean_fhir_json + candidate_trials_raw from state
  - Output: verified_matches + rejected_trials stored in state

What it does:
  1. Iterates over each trial in candidate_trials_raw.
  2. For EACH trial, starts a FRESH Claude conversation (isolated sub-turn).
     → This is the context compaction strategy: trial eligibility text is
       massive (often 2,000+ words). If we fed all 20 trials at once we'd
       blow through the context window AND force Claude to juggle 20 sets
       of inclusion/exclusion rules simultaneously.
  3. Each isolated call asks Claude to render a PASS/FAIL verdict with reason.
  4. PASS → RawTrial is promoted to VerifiedMatch in state.verified_matches
     FAIL → logged as RejectedTrial in state.rejected_trials

Why per-trial isolation matters:
  Clinical eligibility criteria contain many negative conditions ("must NOT
  have had prior X", "exclude if platelet count < Y"). If we batch trials,
  Claude tends to conflate exclusion criteria across trials — a rejection
  reason from Trial A can bleed into Trial B's evaluation. Isolation prevents
  this entirely.

Unit normalization:
  The system prompt instructs Claude to normalize units before comparison.
  E.g., if the chart shows ANC = 1.8 K/μL and the trial requires
  ANC ≥ 1500/μL (same thing, different notation), Claude recognizes the
  equivalence and does not reject on a unit mismatch.
"""

from __future__ import annotations

import json
import os
from typing import Any

import anthropic

from utils.logger import get_logger
from utils.state import (
    FHIRPayload,
    PipelineState,
    RawTrial,
    RejectedTrial,
    VerifiedMatch,
)

logger = get_logger(__name__)

_MODEL: str = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a senior research nurse evaluating clinical trial eligibility.

You will receive:
1. An anonymized patient profile (FHIR JSON)
2. A single clinical trial's eligibility criteria

Your task:
- Carefully read ALL inclusion AND exclusion criteria
- Check each criterion against the patient's profile
- Pay special attention to:
  * Lab value thresholds (e.g., platelet counts, creatinine, HbA1c)
  * Prior treatment requirements or contraindications
  * Age range restrictions
  * Disease stage/severity requirements
  * Time-based exclusions (e.g., "no prior treatment within 6 months")

UNIT NORMALIZATION — CRITICAL:
- Always normalize units before comparing numeric values
- Common equivalencies:
  * ANC: K/μL = K/uL = 10^3/μL = x10^9/L (divide by 1 if same scale)
  * 1 K/μL = 1,000/μL = 1 x10^9/L
  * Platelet counts: K/μL and 10^3/μL are identical
  * If chart says 1.8 K/μL and trial requires ≥1500/μL → 1800/μL ≥ 1500/μL → PASS
- When in doubt about unit equivalence, flag it but do not reject solely on unit mismatch

VERDICT FORMAT — respond with EXACTLY this JSON structure, nothing else:
{
  "verdict": "PASS" or "REJECT",
  "reason": "<one sentence explaining the key qualifier or disqualifier>",
  "eligibility_summary": "<2-3 sentences summarizing why the patient qualifies — only if PASS>",
  "primary_location": "<city, country of first listed location or 'Not specified'>",
  "phase": "<trial phase as listed>"
}

RULES:
- If a patient fails even ONE exclusion criterion → REJECT
- Do not make assumptions about missing data — if a required value isn't in the profile, note it as unknown but do not auto-reject
- Output ONLY the JSON verdict, no preamble
"""


# ── Agent class ───────────────────────────────────────────────────────────────

class EvaluatorAgent:
    """
    Subagent 3: Evaluates each trial in an isolated sub-turn loop.

    Context compaction strategy:
        Each trial is evaluated in a completely separate Claude API call.
        No message history is retained between trials. This keeps per-call
        context lean (~2-4K tokens) regardless of how many trials there are.
    """

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = _MODEL
        logger.info(f"EvaluatorAgent initialized with model={self.model}")

    def run(self, state: PipelineState) -> PipelineState:
        """
        Evaluate each candidate trial against the patient's FHIR profile.

        Args:
            state: Pipeline state with clean_fhir_json and candidate_trials_raw.

        Returns:
            Updated state with verified_matches and rejected_trials populated.
        """
        logger.info("─── Subagent 3: Evaluator started ───")

        if state.clean_fhir_json is None:
            state.add_error(
                agent="EvaluatorAgent",
                error_type="MissingInput",
                message="clean_fhir_json is None",
                recoverable=False,
            )
            return state

        if not state.candidate_trials_raw:
            logger.warning("No candidate trials to evaluate")
            state.add_error(
                agent="EvaluatorAgent",
                error_type="EmptyInput",
                message="candidate_trials_raw is empty — Searcher may have returned no results.",
                recoverable=True,
            )
            return state

        patient_json_str: str = state.clean_fhir_json.model_dump_json(indent=2)
        total = len(state.candidate_trials_raw)

        logger.info(f"Evaluating {total} trials (isolated sub-turn per trial)")

        for idx, trial in enumerate(state.candidate_trials_raw, start=1):
            logger.info(f"Evaluating trial {idx}/{total}: {trial.nct_id} — {trial.official_title[:60]}...")
            try:
                self._evaluate_single_trial(
                    trial=trial,
                    patient_json_str=patient_json_str,
                    state=state,
                )
            except anthropic.APIError as exc:
                logger.error(f"API error evaluating {trial.nct_id}: {exc}")
                state.add_error(
                    agent="EvaluatorAgent",
                    error_type="APIError",
                    message=f"Trial {trial.nct_id}: {exc}",
                    recoverable=True,
                )
            except Exception as exc:
                logger.error(f"Unexpected error evaluating {trial.nct_id}: {exc}", exc_info=True)
                state.add_error(
                    agent="EvaluatorAgent",
                    error_type="UnexpectedError",
                    message=f"Trial {trial.nct_id}: {exc}",
                    recoverable=True,
                )

        state.total_trials_evaluated = total

        logger.info(
            f"Evaluator complete — "
            f"PASS: {len(state.verified_matches)}, "
            f"REJECT: {len(state.rejected_trials)}"
        )
        return state

    def _evaluate_single_trial(
        self,
        trial: RawTrial,
        patient_json_str: str,
        state: PipelineState,
    ) -> None:
        """
        Evaluate one trial in an isolated Claude call.

        CONTEXT COMPACTION: We create a brand-new messages list for every
        trial. No history from previous trial evaluations is carried forward.
        This prevents cross-trial context contamination and keeps token usage
        predictable.

        Args:
            trial:            The RawTrial to evaluate.
            patient_json_str: Serialized FHIRPayload for the patient.
            state:            Pipeline state (mutated in-place).
        """
        # ── Fresh context per trial ──
        user_message: str = (
            "PATIENT PROFILE (anonymized FHIR JSON):\n"
            f"```json\n{patient_json_str}\n```\n\n"
            "CLINICAL TRIAL ELIGIBILITY CRITERIA:\n"
            f"Trial: {trial.nct_id} — {trial.official_title}\n"
            f"Phase: {trial.phase}\n"
            f"Locations: {', '.join(trial.locations[:3]) if trial.locations else 'Not specified'}\n\n"
            f"```\n{trial.eligibility_criteria}\n```\n\n"
            "Evaluate eligibility and return your JSON verdict."
        )

        # ── Isolated API call (no history carried over) ──
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_verdict_str: str = response.content[0].text.strip()

        # Strip markdown fences if present
        if raw_verdict_str.startswith("```"):
            lines = raw_verdict_str.split("\n")
            raw_verdict_str = "\n".join(
                line for line in lines if not line.startswith("```")
            ).strip()

        verdict_data: dict[str, Any] = json.loads(raw_verdict_str)
        verdict: str = verdict_data.get("verdict", "REJECT").upper()
        reason: str = verdict_data.get("reason", "No reason provided.")

        logger.info(f"  {trial.nct_id} → {verdict}: {reason[:80]}")

        if verdict == "PASS":
            state.verified_matches.append(
                VerifiedMatch(
                    nct_id=trial.nct_id,
                    official_title=trial.official_title,
                    phase=verdict_data.get("phase", trial.phase),
                    primary_location=verdict_data.get("primary_location", "Not specified"),
                    eligibility_summary=verdict_data.get("eligibility_summary", reason),
                    contact_name=trial.contact_name,
                    contact_email=trial.contact_email,
                    contact_phone=trial.contact_phone,
                )
            )
        else:
            state.rejected_trials.append(
                RejectedTrial(
                    nct_id=trial.nct_id,
                    official_title=trial.official_title,
                    rejection_reason=reason,
                )
            )
