"""
orchestrator/master.py
───────────────────────
Master Orchestrator — The Command Center

This is the top-level controller for the entire multi-agent pipeline.
It owns the PipelineState, sequences the subagents, handles exceptions
from any downstream agent, and reports the final outcome.

Architecture:
  The orchestrator does NOT call the Claude API itself — it delegates all
  LLM work to the specialized subagents. Its only job is lifecycle management:
    1. Initialize PipelineState from the raw chart
    2. Call Subagent 1 (Anonymizer)       → populates clean_fhir_json
    3. Call Subagent 2 (Searcher)         → populates candidate_trials_raw
    4. Call Subagent 3 (Evaluator)        → populates verified_matches
    5. Call Subagent 4 (Scribe)           → populates report_markdown
    6. Return the final PipelineState

Error handling strategy:
  - Each agent catches its own exceptions and stores them in state.errors
  - The orchestrator checks state.has_fatal_errors() after each agent
  - If a fatal error occurs, the orchestrator stops the pipeline and returns
    the partial state (so the caller can see exactly where it failed)
  - Non-fatal errors (e.g., Evaluator failing on one trial) let the
    pipeline continue — we still generate a report with whatever matched

Timeout handling:
  We wrap each subagent call in a try/except that catches TimeoutError and
  generic exceptions, converts them to PipelineErrors, and records the
  bottleneck agent name.
"""

from __future__ import annotations

import time
from typing import Optional

from agents.anonymizer import AnonymizerAgent
from agents.searcher import SearcherAgent
from agents.evaluator import EvaluatorAgent
from agents.scribe import ScribeAgent
from utils.logger import get_logger
from utils.state import PipelineState

logger = get_logger(__name__)


class MasterOrchestrator:
    """
    Top-level coordinator for the Clinical Trial Matcher pipeline.

    Usage:
        orchestrator = MasterOrchestrator()
        state = orchestrator.run(raw_chart_text)
        print(state.report_markdown)
    """

    def __init__(self) -> None:
        # Instantiate all subagents — they share the same Anthropic client
        # indirectly (each creates its own, keyed to the same ANTHROPIC_API_KEY)
        self.anonymizer = AnonymizerAgent()
        self.searcher = SearcherAgent()
        self.evaluator = EvaluatorAgent()
        self.scribe = ScribeAgent()
        logger.info("MasterOrchestrator initialized with all 4 subagents")

    def run(self, raw_chart_text: str) -> PipelineState:
        """
        Execute the full pipeline end-to-end.

        Args:
            raw_chart_text: Raw text content of the patient chart (.txt or .pdf).

        Returns:
            Final PipelineState containing:
              - report_markdown: the physician dossier (or partial results)
              - errors: list of any PipelineError objects
              - all intermediate state keys for debugging
        """
        pipeline_start = time.time()
        logger.info("═══════════════════════════════════════════════")
        logger.info("  Clinical Trial Matcher — Pipeline Starting   ")
        logger.info("═══════════════════════════════════════════════")

        # ── Initialize state ──
        state = PipelineState(raw_payload=raw_chart_text)
        logger.info(f"Raw chart loaded — {len(raw_chart_text)} characters")

        # ── Stage 1: Anonymizer ──
        state = self._run_stage(
            agent_name="Anonymizer",
            stage_fn=lambda: self.anonymizer.run(state),
            state=state,
        )
        if state.has_fatal_errors():
            return self._abort(state, "Anonymizer", pipeline_start)

        # ── Stage 2: Searcher ──
        state = self._run_stage(
            agent_name="Searcher",
            stage_fn=lambda: self.searcher.run(state),
            state=state,
        )
        if state.has_fatal_errors():
            return self._abort(state, "Searcher", pipeline_start)

        # ── Stage 3: Evaluator ──
        state = self._run_stage(
            agent_name="Evaluator",
            stage_fn=lambda: self.evaluator.run(state),
            state=state,
        )
        # Evaluator errors are non-fatal (partial results are acceptable)
        # We continue to Scribe even if some trials errored

        # ── Stage 4: Scribe ──
        state = self._run_stage(
            agent_name="Scribe",
            stage_fn=lambda: self.scribe.run(state),
            state=state,
        )

        # ── Pipeline complete ──
        elapsed = time.time() - pipeline_start
        self._log_summary(state, elapsed)

        return state

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _run_stage(
        self,
        agent_name: str,
        stage_fn,
        state: PipelineState,
    ) -> PipelineState:
        """
        Run a single pipeline stage with top-level exception handling.

        This ensures that even if an agent raises an unhandled exception
        (e.g., network error, import error), the orchestrator catches it,
        records it as a fatal PipelineError, and returns the state cleanly
        rather than crashing the process.

        Args:
            agent_name: Human-readable name for logging.
            stage_fn:   Callable that runs the agent and returns updated state.
            state:      Current pipeline state.

        Returns:
            Updated PipelineState (same object, mutated by agent).
        """
        stage_start = time.time()
        logger.info(f"Starting stage: {agent_name}")

        try:
            updated_state: PipelineState = stage_fn()
            elapsed = time.time() - stage_start
            logger.info(f"Stage {agent_name} complete in {elapsed:.2f}s")
            return updated_state

        except TimeoutError as exc:
            logger.error(f"TIMEOUT in {agent_name}: {exc}")
            state.add_error(
                agent=agent_name,
                error_type="Timeout",
                message=f"{agent_name} timed out: {exc}",
                recoverable=False,
            )
            return state

        except MemoryError as exc:
            logger.error(f"MEMORY ERROR in {agent_name}: {exc}")
            state.add_error(
                agent=agent_name,
                error_type="MemoryError",
                message=f"{agent_name} ran out of memory: {exc}",
                recoverable=False,
            )
            return state

        except Exception as exc:
            logger.error(
                f"UNHANDLED EXCEPTION in {agent_name}: {type(exc).__name__}: {exc}",
                exc_info=True,
            )
            state.add_error(
                agent=agent_name,
                error_type=type(exc).__name__,
                message=f"Unhandled exception in {agent_name}: {exc}",
                recoverable=False,
            )
            return state

    def _abort(
        self,
        state: PipelineState,
        bottleneck_agent: str,
        pipeline_start: float,
    ) -> PipelineState:
        """
        Called when a fatal error stops the pipeline early.
        Generates a minimal error report so the caller always gets output.
        """
        elapsed = time.time() - pipeline_start
        logger.error(
            f"Pipeline aborted at stage '{bottleneck_agent}' after {elapsed:.2f}s. "
            f"Errors: {[e.message for e in state.errors]}"
        )

        # Generate a minimal failure report so main.py can still write output
        error_lines = "\n".join([
            f"- **{e.agent}** ({e.error_type}): {e.message}"
            for e in state.errors
        ])
        state.report_markdown = (
            f"# Clinical Trial Matcher — Pipeline Aborted\n\n"
            f"The pipeline was stopped by a fatal error in the **{bottleneck_agent}** stage.\n\n"
            f"## Errors\n\n{error_lines}\n\n"
            f"Please check logs for details and retry.\n"
        )
        return state

    def _log_summary(self, state: PipelineState, elapsed: float) -> None:
        """Log the final pipeline run summary."""
        logger.info("═══════════════════════════════════════════════")
        logger.info("  Pipeline Complete                            ")
        logger.info(f"  Total time:          {elapsed:.2f}s")
        logger.info(f"  Trials fetched:      {state.total_trials_fetched}")
        logger.info(f"  Trials evaluated:    {state.total_trials_evaluated}")
        logger.info(f"  Verified matches:    {len(state.verified_matches)}")
        logger.info(f"  Rejected trials:     {len(state.rejected_trials)}")
        logger.info(f"  Pipeline errors:     {len(state.errors)}")
        logger.info(f"  Report length:       {len(state.report_markdown)} chars")
        logger.info("═══════════════════════════════════════════════")

        if state.errors:
            logger.warning("Pipeline completed with errors:")
            for error in state.errors:
                level = "ERROR" if not error.recoverable else "WARN"
                logger.warning(f"  [{level}] {error.agent}: {error.message}")
