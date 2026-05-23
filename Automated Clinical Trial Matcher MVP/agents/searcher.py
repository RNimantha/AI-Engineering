"""
agents/searcher.py
───────────────────
Subagent 2: API Query Extractor (The Searcher)

Responsibility:
  - Input:  clean_fhir_json (FHIRPayload) from state
  - Output: candidate_trials_raw (list[RawTrial]) stored in state

What it does:
  1. Uses Claude in an agentic tool-use loop to extract the primary
     condition from the FHIR JSON and call the `search_clinical_trials` tool.
  2. The PreToolUse HIPAA hook fires BEFORE the tool executes to ensure
     no PII leaks to ClinicalTrials.gov.
  3. The tool result is stored back in the pipeline state.

Why use an agentic loop for a simple API call?
  The Searcher uses tool use so Claude can reason about which condition
  is most relevant for the trial search (the FHIR JSON may list 5 conditions
  — Claude picks the primary one). This is better than hard-coding
  "use conditions[0]" since oncology charts often list co-morbidities
  before the primary diagnosis.

Context compaction note:
  The Searcher conversation is intentionally short — we do NOT retain the
  full chart in this agent's context. We only pass the FHIR JSON summary.
  This keeps the message history small and avoids leaking the original
  raw text (which may have contained PII before anonymization).
"""

from __future__ import annotations

import json
import os
from typing import Any

import anthropic

from tools.clinical_trials_api import (
    CLINICAL_TRIALS_TOOL_SCHEMA,
    search_trials,
)
from hooks.hipaa_guardrail import pre_tool_use_hook, HIPAAViolationError
from utils.logger import get_logger
from utils.state import PipelineState, RawTrial

logger = get_logger(__name__)

_MODEL: str = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a clinical research data engineer. Your job is to:

1. Analyze the provided anonymized patient FHIR JSON.
2. Identify the PRIMARY medical condition that should be used to search for
   clinical trials (usually the main diagnosis, not co-morbidities).
3. Call the `search_clinical_trials` tool with:
   - condition: The primary condition in standard medical terminology
   - max_results: 20

RULES:
- Use precise medical terminology (e.g., "non-small cell lung cancer" not "lung cancer").
- Do NOT include patient names, ages, IDs, or any personal data in the tool call.
- The condition field must contain only the disease/condition name — nothing else.
- After the tool returns results, respond with exactly: SEARCH_COMPLETE
"""


# ── Agent class ───────────────────────────────────────────────────────────────

class SearcherAgent:
    """
    Subagent 2: Queries ClinicalTrials.gov using an agentic tool-use loop.

    The agentic loop:
      Turn 1: User sends FHIR JSON → Claude decides to call search_clinical_trials
      Hook:   pre_tool_use_hook validates payload is PII-free
      Tool:   search_trials() hits ClinicalTrials.gov API
      Turn 2: Tool result returned → Claude confirms SEARCH_COMPLETE
    """

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = _MODEL
        logger.info(f"SearcherAgent initialized with model={self.model}")

    def run(self, state: PipelineState) -> PipelineState:
        """
        Execute the trial search pass.

        Args:
            state: Pipeline state containing clean_fhir_json.

        Returns:
            Updated state with candidate_trials_raw populated.
        """
        logger.info("─── Subagent 2: Searcher started ───")

        if state.clean_fhir_json is None:
            state.add_error(
                agent="SearcherAgent",
                error_type="MissingInput",
                message="clean_fhir_json is None — Anonymizer may have failed.",
                recoverable=False,
            )
            return state

        try:
            trials = self._run_agentic_loop(state.clean_fhir_json.model_dump_json(indent=2))
            state.candidate_trials_raw = trials
            state.total_trials_fetched = len(trials)
            logger.info(f"Searcher complete — {len(trials)} trials fetched")

        except HIPAAViolationError as exc:
            logger.error(f"HIPAA BLOCK in Searcher: {exc}")
            state.add_error(
                agent="SearcherAgent",
                error_type="HIPAAViolation",
                message=str(exc),
                recoverable=False,
            )
        except anthropic.APIError as exc:
            logger.error(f"Anthropic API error in Searcher: {exc}")
            state.add_error(
                agent="SearcherAgent",
                error_type="APIError",
                message=str(exc),
                recoverable=True,
            )
        except Exception as exc:
            logger.error(f"Unexpected error in Searcher: {exc}", exc_info=True)
            state.add_error(
                agent="SearcherAgent",
                error_type="UnexpectedError",
                message=str(exc),
                recoverable=True,
            )

        return state

    def _run_agentic_loop(self, fhir_json_str: str) -> list[RawTrial]:
        """
        Run the tool-use agentic loop to search for trials.

        Returns:
            List of RawTrial objects from the API.

        Raises:
            HIPAAViolationError: If the PreToolUse hook detects PII.
            RuntimeError:        If the agent loop exceeds max iterations.
        """
        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": (
                    "Here is the anonymized patient profile in FHIR JSON format. "
                    "Identify the primary condition and search for recruiting clinical trials:\n\n"
                    f"```json\n{fhir_json_str}\n```"
                ),
            }
        ]

        tools = [CLINICAL_TRIALS_TOOL_SCHEMA]
        max_iterations = 5
        iteration = 0
        fetched_trials: list[RawTrial] = []

        while iteration < max_iterations:
            iteration += 1
            logger.debug(f"Searcher agentic loop iteration {iteration}")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=_SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )

            # ── Check if Claude wants to use a tool ──
            if response.stop_reason == "tool_use":
                tool_results: list[dict[str, Any]] = []

                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_name: str = block.name
                    tool_input: dict[str, Any] = block.input

                    logger.info(f"Claude calling tool: {tool_name} with input: {tool_input}")

                    # ── PreToolUse HIPAA hook ──
                    pre_tool_use_hook(tool_name, tool_input)  # Raises HIPAAViolationError if PII found

                    # ── Execute tool ──
                    if tool_name == "search_clinical_trials":
                        raw_results = search_trials(
                            condition=tool_input["condition"],
                            max_results=tool_input.get("max_results", 20),
                        )
                        # Convert dicts back to RawTrial objects
                        fetched_trials = [RawTrial(**t) for t in raw_results]

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(raw_results),
                        })
                    else:
                        # Unknown tool — return empty result
                        logger.warning(f"Unknown tool called: {tool_name}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"error": f"Unknown tool: {tool_name}"}),
                        })

                # Append assistant message and tool results to history
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

            # ── Claude is done ──
            elif response.stop_reason == "end_turn":
                logger.debug("Searcher agentic loop complete (end_turn)")
                break

            else:
                logger.warning(f"Unexpected stop_reason: {response.stop_reason}")
                break

        if iteration >= max_iterations:
            raise RuntimeError(f"Searcher exceeded max_iterations={max_iterations}")

        return fetched_trials
