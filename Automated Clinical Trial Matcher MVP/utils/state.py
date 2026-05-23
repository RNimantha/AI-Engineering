"""
utils/state.py
──────────────
Centralized state container for the multi-agent pipeline.

Design decision: Rather than passing individual arguments between agents,
we use a single mutable dict (PipelineState) that flows through the
orchestrator. This mirrors the "shared blackboard" pattern common in
multi-agent architectures — every agent reads what it needs and writes
its output back to a named key.

The Pydantic model here acts as the schema contract:
  - raw_payload         → set by the orchestrator from the input file
  - clean_fhir_json     → set by Subagent 1 (Anonymizer)
  - candidate_trials_raw → set by Subagent 2 (Searcher)
  - verified_matches    → set by Subagent 3 (Evaluator)
  - report_markdown     → set by Subagent 4 (Scribe)
  - errors              → appended by any agent that catches an exception
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ── FHIR-aligned patient data model ──────────────────────────────────────────

class LabResult(BaseModel):
    """A single lab measurement, e.g. HbA1c = 8.2 %"""
    test: str
    value: Any          # numeric or string (e.g. "Positive")
    unit: str = ""
    reference_range: str = ""


class PatientProfile(BaseModel):
    """Anonymized patient demographics."""
    age_range: str       # e.g. "45-50 years old"
    gender: str = ""
    anonymized: bool = True


class FHIRPayload(BaseModel):
    """
    Simplified HL7 FHIR-aligned JSON.

    Note: This is NOT a full FHIR R4 bundle — it's a pragmatic subset
    designed to carry only the fields the Evaluator needs to match
    against trial eligibility criteria.
    """
    patient: PatientProfile
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    lab_results: list[LabResult] = Field(default_factory=list)
    prior_treatments: list[str] = Field(default_factory=list)
    contraindications: list[str] = Field(default_factory=list)


# ── Trial data models ─────────────────────────────────────────────────────────

class RawTrial(BaseModel):
    """Raw trial object returned by the ClinicalTrials.gov API v2."""
    nct_id: str
    official_title: str
    eligibility_criteria: str
    locations: list[str] = Field(default_factory=list)
    phase: str = "N/A"
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""


class VerifiedMatch(BaseModel):
    """A trial that passed all eligibility checks."""
    nct_id: str
    official_title: str
    phase: str
    primary_location: str
    eligibility_summary: str        # Why the patient qualifies
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""


class RejectedTrial(BaseModel):
    """A trial that failed at least one exclusion criterion."""
    nct_id: str
    official_title: str
    rejection_reason: str           # Single sentence explaining the failure


# ── Pipeline error model ──────────────────────────────────────────────────────

class PipelineError(BaseModel):
    """Structured error record from any agent or hook."""
    agent: str
    error_type: str
    message: str
    recoverable: bool = True


# ── Master state dict ─────────────────────────────────────────────────────────

class PipelineState(BaseModel):
    """
    Single source of truth for the entire pipeline run.

    The orchestrator initializes this and passes it (by reference as a dict
    via .model_dump()) to each subagent which mutates their designated key.
    """
    # ── Input ──
    raw_payload: str = ""                       # Original chart text

    # ── Agent outputs ──
    clean_fhir_json: Optional[FHIRPayload] = None
    candidate_trials_raw: list[RawTrial] = Field(default_factory=list)
    verified_matches: list[VerifiedMatch] = Field(default_factory=list)
    rejected_trials: list[RejectedTrial] = Field(default_factory=list)
    report_markdown: str = ""

    # ── Diagnostics ──
    errors: list[PipelineError] = Field(default_factory=list)
    total_trials_fetched: int = 0
    total_trials_evaluated: int = 0

    def add_error(self, agent: str, error_type: str, message: str, recoverable: bool = True) -> None:
        """Convenience method to append a structured error."""
        self.errors.append(PipelineError(
            agent=agent,
            error_type=error_type,
            message=message,
            recoverable=recoverable
        ))

    def has_fatal_errors(self) -> bool:
        """Return True if any non-recoverable error was recorded."""
        return any(not e.recoverable for e in self.errors)
