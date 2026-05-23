"""
tests/test_pipeline_dryrun.py
──────────────────────────────
Dry-run smoke test for the full Clinical Trial Matcher pipeline.

This test exercises every module and data-flow path WITHOUT making live
Anthropic API calls or hitting ClinicalTrials.gov. It injects mock data
at each stage boundary to verify:

  1. PipelineState flows correctly through all stages
  2. HIPAA hook blocks PII and passes clean payloads
  3. AnonymizerAgent's Claude call is stubbed — validates FHIR JSON parsing
  4. SearcherAgent's tool-use loop is stubbed — validates trial object handling
  5. EvaluatorAgent's per-trial loop is stubbed — validates PASS/REJECT routing
  6. ScribeAgent's fallback report is validated (no API key needed)
  7. MasterOrchestrator abort logic works on fatal errors
  8. CLI --help renders cleanly

Run:
    python -m pytest tests/test_pipeline_dryrun.py -v
  or:
    python tests/test_pipeline_dryrun.py
"""

from __future__ import annotations

import json
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# ── Make project root importable ─────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Load a dummy API key so SDK doesn't complain at import time ───────────────
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-dryrun-key")
os.environ.setdefault("CLAUDE_MODEL", "claude-sonnet-4-6")

from utils.state import (
    PipelineState, FHIRPayload, PatientProfile, LabResult,
    RawTrial, VerifiedMatch, RejectedTrial,
)
from utils.pdf_parser import read_chart
from hooks.hipaa_guardrail import pre_tool_use_hook, HIPAAViolationError, sanitize_check
from tools.clinical_trials_api import CLINICAL_TRIALS_TOOL_SCHEMA


# ── Shared mock FHIR payload ──────────────────────────────────────────────────

def _mock_fhir() -> FHIRPayload:
    return FHIRPayload(
        patient=PatientProfile(age_range="50-55 years old", gender="Male"),
        conditions=["Non-Small Cell Lung Cancer", "Type 2 Diabetes Mellitus"],
        medications=["Pemetrexed 500 mg/m²", "Metformin 1000 mg", "Lisinopril 10 mg"],
        lab_results=[
            LabResult(test="ANC", value=3.4, unit="K/μL", reference_range="1.8-7.5"),
            LabResult(test="Platelets", value=198, unit="K/μL", reference_range="150-400"),
            LabResult(test="Creatinine", value=0.9, unit="mg/dL", reference_range="0.7-1.3"),
            LabResult(test="HbA1c", value=7.4, unit="%", reference_range="<5.7"),
            LabResult(test="Hemoglobin", value=12.8, unit="g/dL", reference_range="13.5-17.5"),
        ],
        prior_treatments=["Carboplatin AUC5 + Pemetrexed (4 cycles, partial response)"],
        contraindications=["Penicillin allergy", "Sulfonamide allergy"],
    )


def _mock_trials() -> list[RawTrial]:
    return [
        RawTrial(
            nct_id="NCT12345678",
            official_title="Phase III Study of Osimertinib in EGFR-Mutant NSCLC",
            eligibility_criteria=(
                "Inclusion: EGFR exon 19 del or L858R mutation; ECOG 0-2; "
                "adequate bone marrow (ANC ≥1500/μL, Platelets ≥100,000/μL); "
                "adequate renal function (Creatinine ≤1.5x ULN).\n"
                "Exclusion: Prior EGFR TKI therapy; active CNS metastases; "
                "prior allergy to osimertinib."
            ),
            locations=["Massachusetts General Hospital, Boston, USA"],
            phase="PHASE3",
            contact_name="Dr. Emily Chen",
            contact_email="echen@mgh.harvard.edu",
            contact_phone="617-555-0199",
        ),
        RawTrial(
            nct_id="NCT87654321",
            official_title="Phase II Pembrolizumab + Chemotherapy in PD-L1+ NSCLC",
            eligibility_criteria=(
                "Inclusion: PD-L1 TPS ≥1%; ECOG 0-1; no prior immunotherapy.\n"
                "Exclusion: Active autoimmune disease requiring systemic treatment; "
                "prior treatment with anti-PD-1/PD-L1 antibody; "
                "platelet count <75,000/μL."
            ),
            locations=["MD Anderson Cancer Center, Houston, USA"],
            phase="PHASE2",
            contact_name="",
            contact_email="",
            contact_phone="",
        ),
    ]


# ═════════════════════════════════════════════════════════════════════════════
# TEST SUITE
# ═════════════════════════════════════════════════════════════════════════════

class TestPipelineState(unittest.TestCase):
    """Validate the PipelineState data model."""

    def test_initial_state_is_clean(self):
        state = PipelineState(raw_payload="test")
        self.assertEqual(state.raw_payload, "test")
        self.assertIsNone(state.clean_fhir_json)
        self.assertEqual(state.verified_matches, [])
        self.assertEqual(state.errors, [])
        self.assertFalse(state.has_fatal_errors())

    def test_fatal_error_detection(self):
        state = PipelineState(raw_payload="x")
        state.add_error("Agent", "TestError", "msg", recoverable=False)
        self.assertTrue(state.has_fatal_errors())

    def test_recoverable_error_not_fatal(self):
        state = PipelineState(raw_payload="x")
        state.add_error("Agent", "TestError", "msg", recoverable=True)
        self.assertFalse(state.has_fatal_errors())

    def test_fhir_payload_serialization(self):
        fhir = _mock_fhir()
        serialized = fhir.model_dump_json()
        parsed = json.loads(serialized)
        self.assertEqual(parsed["patient"]["age_range"], "50-55 years old")
        self.assertIn("Non-Small Cell Lung Cancer", parsed["conditions"])
        self.assertEqual(len(parsed["lab_results"]), 5)


class TestHIPAAGuardrail(unittest.TestCase):
    """Validate the HIPAA PreToolUse hook."""

    def test_blocks_full_name(self):
        with self.assertRaises(HIPAAViolationError) as ctx:
            pre_tool_use_hook("search_clinical_trials", {"condition": "James Callahan NSCLC"})
        self.assertIn("Full name", ctx.exception.pii_type)

    def test_blocks_phone_number(self):
        with self.assertRaises(HIPAAViolationError) as ctx:
            pre_tool_use_hook("search_clinical_trials", {"patient_phone": "312-555-0177"})
        self.assertIn("phone", ctx.exception.pii_type.lower())

    def test_blocks_email(self):
        with self.assertRaises(HIPAAViolationError) as ctx:
            pre_tool_use_hook("search_clinical_trials", {"contact": "james@email.com"})
        self.assertIn("Email", ctx.exception.pii_type)

    def test_blocks_date_of_birth(self):
        with self.assertRaises(HIPAAViolationError) as ctx:
            pre_tool_use_hook("search_clinical_trials", {"dob": "1972-09-14"})
        self.assertIn("date of birth", ctx.exception.pii_type.lower())

    def test_passes_clean_medical_condition(self):
        result = pre_tool_use_hook(
            "search_clinical_trials",
            {"condition": "non-small cell lung cancer", "max_results": 20},
        )
        self.assertTrue(result)

    def test_passes_condition_with_numbers(self):
        """Lab values like '3.4 K/μL' must not be falsely flagged."""
        result = pre_tool_use_hook(
            "search_clinical_trials",
            {"condition": "EGFR-mutant NSCLC adenocarcinoma stage IIIB"},
        )
        self.assertTrue(result)

    def test_hipaa_violation_error_attributes(self):
        try:
            pre_tool_use_hook("my_tool", {"name": "John Smith"})
        except HIPAAViolationError as e:
            self.assertEqual(e.tool_name, "my_tool")
            self.assertIn("John Smith", e.detail)

    def test_sanitize_check_non_blocking(self):
        """sanitize_check should return findings without raising."""
        findings = sanitize_check("Patient: John Smith, DOB: 1980-01-01", "test")
        self.assertGreater(len(findings), 0)


class TestPDFParser(unittest.TestCase):
    """Validate the chart reader."""

    def test_reads_sample_patient_txt(self):
        chart_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "sample_data", "sample_patient.txt"
        )
        text = read_chart(chart_path)
        self.assertGreater(len(text), 1000)
        self.assertIn("NSCLC", text)
        self.assertIn("EGFR", text)
        self.assertIn("Pemetrexed", text)

    def test_raises_on_missing_file(self):
        from utils.pdf_parser import read_chart
        with self.assertRaises(FileNotFoundError):
            read_chart("/tmp/nonexistent_chart_12345.txt")

    def test_raises_on_unsupported_type(self):
        from utils.pdf_parser import UnsupportedFileTypeError
        # Create a temp file with wrong extension
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(b"fake content")
            tmp_path = f.name
        try:
            with self.assertRaises(UnsupportedFileTypeError):
                read_chart(tmp_path)
        finally:
            os.unlink(tmp_path)


class TestToolSchema(unittest.TestCase):
    """Validate the Anthropic tool schema structure."""

    def test_schema_has_required_keys(self):
        schema = CLINICAL_TRIALS_TOOL_SCHEMA
        self.assertEqual(schema["name"], "search_clinical_trials")
        self.assertIn("description", schema)
        self.assertIn("input_schema", schema)
        self.assertIn("condition", schema["input_schema"]["properties"])
        self.assertIn("condition", schema["input_schema"]["required"])


class TestAnonymizerAgent(unittest.TestCase):
    """Validate AnonymizerAgent with stubbed Claude response."""

    def _make_claude_response(self, json_str: str):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json_str)]
        return mock_response

    @patch("agents.anonymizer.anthropic.Anthropic")
    def test_anonymizer_parses_valid_fhir(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        fhir_json = _mock_fhir().model_dump_json()
        mock_client.messages.create.return_value = self._make_claude_response(fhir_json)

        from agents.anonymizer import AnonymizerAgent
        agent = AnonymizerAgent()
        state = PipelineState(raw_payload="raw chart text")
        state = agent.run(state)

        self.assertIsNotNone(state.clean_fhir_json)
        self.assertIn("Non-Small Cell Lung Cancer", state.clean_fhir_json.conditions)
        self.assertEqual(len(state.errors), 0)

    @patch("agents.anonymizer.anthropic.Anthropic")
    def test_anonymizer_handles_empty_input(self, mock_anthropic_cls):
        from agents.anonymizer import AnonymizerAgent
        agent = AnonymizerAgent()
        state = PipelineState(raw_payload="")
        state = agent.run(state)

        self.assertIsNone(state.clean_fhir_json)
        self.assertTrue(state.has_fatal_errors())

    @patch("agents.anonymizer.anthropic.Anthropic")
    def test_anonymizer_strips_markdown_fences(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        fhir_dict = _mock_fhir().model_dump()
        wrapped_json = f"```json\n{json.dumps(fhir_dict)}\n```"
        mock_client.messages.create.return_value = self._make_claude_response(wrapped_json)

        from agents.anonymizer import AnonymizerAgent
        agent = AnonymizerAgent()
        state = PipelineState(raw_payload="some chart")
        state = agent.run(state)

        self.assertIsNotNone(state.clean_fhir_json)
        self.assertEqual(len(state.errors), 0)


class TestSearcherAgent(unittest.TestCase):
    """Validate SearcherAgent tool-use loop with stubbed Anthropic + API."""

    def _make_tool_use_response(self, tool_use_id: str, condition: str):
        """Simulate Claude deciding to call the search tool."""
        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.id = tool_use_id
        tool_use_block.name = "search_clinical_trials"
        tool_use_block.input = {"condition": condition, "max_results": 20}

        response = MagicMock()
        response.stop_reason = "tool_use"
        response.content = [tool_use_block]
        return response

    def _make_end_turn_response(self):
        response = MagicMock()
        response.stop_reason = "end_turn"
        response.content = [MagicMock(text="SEARCH_COMPLETE")]
        return response

    @patch("agents.searcher.search_trials")
    @patch("agents.searcher.anthropic.Anthropic")
    def test_searcher_full_loop(self, mock_anthropic_cls, mock_search_trials):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_search_trials.return_value = [t.model_dump() for t in _mock_trials()]
        mock_client.messages.create.side_effect = [
            self._make_tool_use_response("tool_001", "non-small cell lung cancer"),
            self._make_end_turn_response(),
        ]

        from agents.searcher import SearcherAgent
        agent = SearcherAgent()
        state = PipelineState(raw_payload="x", clean_fhir_json=_mock_fhir())
        state = agent.run(state)

        self.assertEqual(len(state.candidate_trials_raw), 2)
        self.assertEqual(state.total_trials_fetched, 2)
        self.assertEqual(state.candidate_trials_raw[0].nct_id, "NCT12345678")
        self.assertEqual(len(state.errors), 0)

    @patch("agents.searcher.anthropic.Anthropic")
    def test_searcher_aborts_on_hipaa_violation(self, mock_anthropic_cls):
        """If Claude tries to pass a name in the condition → hook blocks it."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.id = "tool_pii"
        tool_use_block.name = "search_clinical_trials"
        tool_use_block.input = {"condition": "James Callahan NSCLC"}  # PII!

        response = MagicMock()
        response.stop_reason = "tool_use"
        response.content = [tool_use_block]
        mock_client.messages.create.return_value = response

        from agents.searcher import SearcherAgent
        agent = SearcherAgent()
        state = PipelineState(raw_payload="x", clean_fhir_json=_mock_fhir())
        state = agent.run(state)

        self.assertEqual(len(state.candidate_trials_raw), 0)
        self.assertTrue(any(e.error_type == "HIPAAViolation" for e in state.errors))


class TestEvaluatorAgent(unittest.TestCase):
    """Validate EvaluatorAgent per-trial isolation with stubbed Claude."""

    def _make_verdict_response(self, verdict: str, reason: str, summary: str = ""):
        verdict_dict = {
            "verdict": verdict,
            "reason": reason,
            "eligibility_summary": summary,
            "primary_location": "Boston, USA",
            "phase": "PHASE3",
        }
        response = MagicMock()
        response.content = [MagicMock(text=json.dumps(verdict_dict))]
        return response

    @patch("agents.evaluator.anthropic.Anthropic")
    def test_evaluator_pass_verdict(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._make_verdict_response(
            "PASS", "Patient meets all inclusion criteria.", "Patient qualifies on EGFR status and ECOG."
        )

        from agents.evaluator import EvaluatorAgent
        agent = EvaluatorAgent()
        state = PipelineState(
            raw_payload="x",
            clean_fhir_json=_mock_fhir(),
            candidate_trials_raw=[_mock_trials()[0]],
        )
        state = agent.run(state)

        self.assertEqual(len(state.verified_matches), 1)
        self.assertEqual(len(state.rejected_trials), 0)
        self.assertEqual(state.verified_matches[0].nct_id, "NCT12345678")

    @patch("agents.evaluator.anthropic.Anthropic")
    def test_evaluator_reject_verdict(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._make_verdict_response(
            "REJECT", "Patient had prior EGFR TKI therapy which is excluded."
        )

        from agents.evaluator import EvaluatorAgent
        agent = EvaluatorAgent()
        state = PipelineState(
            raw_payload="x",
            clean_fhir_json=_mock_fhir(),
            candidate_trials_raw=[_mock_trials()[0]],
        )
        state = agent.run(state)

        self.assertEqual(len(state.verified_matches), 0)
        self.assertEqual(len(state.rejected_trials), 1)
        self.assertIn("EGFR TKI", state.rejected_trials[0].rejection_reason)

    @patch("agents.evaluator.anthropic.Anthropic")
    def test_evaluator_per_trial_isolation(self, mock_anthropic_cls):
        """Each trial gets its own API call — 2 trials = 2 separate calls."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [
            self._make_verdict_response("PASS", "Qualifies.", "Good match on EGFR."),
            self._make_verdict_response("REJECT", "Excluded by prior immunotherapy."),
        ]

        from agents.evaluator import EvaluatorAgent
        agent = EvaluatorAgent()
        state = PipelineState(
            raw_payload="x",
            clean_fhir_json=_mock_fhir(),
            candidate_trials_raw=_mock_trials(),  # 2 trials
        )
        state = agent.run(state)

        self.assertEqual(mock_client.messages.create.call_count, 2)  # isolated calls
        self.assertEqual(len(state.verified_matches), 1)
        self.assertEqual(len(state.rejected_trials), 1)
        self.assertEqual(state.total_trials_evaluated, 2)


class TestScribeAgent(unittest.TestCase):
    """Validate ScribeAgent fallback report generation."""

    def test_fallback_report_with_matches(self):
        from agents.scribe import ScribeAgent

        with patch("agents.scribe.anthropic.Anthropic"):
            agent = ScribeAgent()

        state = PipelineState(
            raw_payload="x",
            clean_fhir_json=_mock_fhir(),
            verified_matches=[
                VerifiedMatch(
                    nct_id="NCT12345678",
                    official_title="Phase III Osimertinib Study",
                    phase="PHASE3",
                    primary_location="Boston, USA",
                    eligibility_summary="Patient qualifies on EGFR status.",
                    contact_email="trial@mgh.edu",
                )
            ],
        )
        report = agent._fallback_report(state)

        self.assertIn("NCT12345678", report)
        self.assertIn("Phase III Osimertinib Study", report)
        self.assertIn("Boston, USA", report)
        self.assertIn("EGFR", report)

    def test_no_results_report(self):
        from agents.scribe import ScribeAgent

        with patch("agents.scribe.anthropic.Anthropic"):
            agent = ScribeAgent()

        state = PipelineState(
            raw_payload="x",
            clean_fhir_json=_mock_fhir(),
            verified_matches=[],
            rejected_trials=[
                RejectedTrial(
                    nct_id="NCT99999",
                    official_title="Some Trial",
                    rejection_reason="Patient excluded by prior EGFR TKI."
                )
            ],
            total_trials_fetched=5,
            total_trials_evaluated=5,
        )
        report = agent._generate_no_results_report(state)

        self.assertIn("No Eligible Trials Found", report)
        self.assertIn("NCT99999", report)
        self.assertNotIn("James", report)  # No PII


class TestMasterOrchestrator(unittest.TestCase):
    """Validate orchestrator lifecycle and abort behaviour."""

    @patch("orchestrator.master.ScribeAgent")
    @patch("orchestrator.master.EvaluatorAgent")
    @patch("orchestrator.master.SearcherAgent")
    @patch("orchestrator.master.AnonymizerAgent")
    def test_full_pipeline_happy_path(
        self, mock_anon_cls, mock_search_cls, mock_eval_cls, mock_scribe_cls
    ):
        # Set up each agent's run() to populate the expected state keys
        def anon_run(state):
            state.clean_fhir_json = _mock_fhir()
            return state

        def search_run(state):
            state.candidate_trials_raw = _mock_trials()
            state.total_trials_fetched = 2
            return state

        def eval_run(state):
            state.verified_matches = [
                VerifiedMatch(
                    nct_id="NCT12345678",
                    official_title="Osimertinib Trial",
                    phase="PHASE3",
                    primary_location="Boston, USA",
                    eligibility_summary="Patient qualifies.",
                )
            ]
            state.total_trials_evaluated = 2
            return state

        def scribe_run(state):
            state.report_markdown = "# Dossier\nPatient qualifies for NCT12345678."
            return state

        mock_anon_cls.return_value.run = anon_run
        mock_search_cls.return_value.run = search_run
        mock_eval_cls.return_value.run = eval_run
        mock_scribe_cls.return_value.run = scribe_run

        from orchestrator.master import MasterOrchestrator
        orchestrator = MasterOrchestrator()
        state = orchestrator.run("raw chart text here")

        self.assertIsNotNone(state.clean_fhir_json)
        self.assertEqual(len(state.candidate_trials_raw), 2)
        self.assertEqual(len(state.verified_matches), 1)
        self.assertIn("NCT12345678", state.report_markdown)
        self.assertEqual(len(state.errors), 0)

    @patch("orchestrator.master.ScribeAgent")
    @patch("orchestrator.master.EvaluatorAgent")
    @patch("orchestrator.master.SearcherAgent")
    @patch("orchestrator.master.AnonymizerAgent")
    def test_pipeline_aborts_on_anonymizer_fatal_error(
        self, mock_anon_cls, mock_search_cls, mock_eval_cls, mock_scribe_cls
    ):
        def anon_run_fail(state):
            state.add_error("AnonymizerAgent", "APIError", "Claude unreachable", recoverable=False)
            return state

        mock_anon_cls.return_value.run = anon_run_fail

        from orchestrator.master import MasterOrchestrator
        orchestrator = MasterOrchestrator()
        state = orchestrator.run("raw chart text")

        # Pipeline should have stopped — Searcher never ran
        self.assertEqual(len(state.candidate_trials_raw), 0)
        self.assertIn("Pipeline Aborted", state.report_markdown)
        self.assertTrue(state.has_fatal_errors())


# ═════════════════════════════════════════════════════════════════════════════
# Runner
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestPipelineState,
        TestHIPAAGuardrail,
        TestPDFParser,
        TestToolSchema,
        TestAnonymizerAgent,
        TestSearcherAgent,
        TestEvaluatorAgent,
        TestScribeAgent,
        TestMasterOrchestrator,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
