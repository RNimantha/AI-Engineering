# Automated Clinical Trial Matcher MVP

A multi-agent system built with the **Anthropic Claude SDK** that takes a raw patient chart (PDF or text), anonymizes it to FHIR JSON, queries ClinicalTrials.gov in real time, evaluates eligibility trial-by-trial, and generates a physician-ready Markdown dossier.

---

## Architecture

```
[Raw Chart (.txt / .pdf)]
        │
        ▼
 ┌─────────────────────────────────────────┐
 │         Master Orchestrator             │
 │       orchestrator/master.py            │
 │  Holds PipelineState · Sequences agents │
 │  Catches exceptions · Reports failures  │
 └──────────┬──────────────────────────────┘
            │
     ┌──────▼──────┐
     │ Subagent 1  │  agents/anonymizer.py
     │  Anonymizer │  Strips PII · Converts to FHIR JSON
     └──────┬──────┘
            │ clean_fhir_json
     ┌──────▼──────┐
     │ Subagent 2  │  agents/searcher.py
     │   Searcher  │  Tool-use loop · PreToolUse HIPAA hook
     └──────┬──────┘  Hits ClinicalTrials.gov API v2
            │ candidate_trials_raw (≤ 20 trials)
     ┌──────▼──────┐
     │ Subagent 3  │  agents/evaluator.py
     │  Evaluator  │  Isolated sub-turn per trial (context compaction)
     └──────┬──────┘  PASS / REJECT with reason
            │ verified_matches
     ┌──────▼──────┐
     │ Subagent 4  │  agents/scribe.py
     │    Scribe   │  Generates Markdown dossier for physician
     └──────┬──────┘
            │
            ▼
      report.md  ✅
```

---

## Quick Start

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3. Run

```bash
# Against the included sample patient chart
python main.py --input sample_data/sample_patient.txt --output report.md

# Against a real PDF
python main.py --input /path/to/chart.pdf --output patient_dossier.md

# Debug mode (verbose logging)
python main.py --input sample_data/sample_patient.txt --verbose
```

### 4. Run tests (no API key required)

```bash
python -m pytest tests/test_pipeline_dryrun.py -v
```

---

## Project Structure

```
├── main.py                         # CLI entry point (Click)
├── requirements.txt
├── .env.example
│
├── orchestrator/
│   └── master.py                   # Master Orchestrator
│
├── agents/
│   ├── anonymizer.py               # Subagent 1: PII stripping + FHIR extraction
│   ├── searcher.py                 # Subagent 2: ClinicalTrials.gov API tool-use loop
│   ├── evaluator.py                # Subagent 3: Per-trial eligibility evaluation
│   └── scribe.py                   # Subagent 4: Markdown dossier generation
│
├── tools/
│   └── clinical_trials_api.py     # ClinicalTrials.gov v2 API wrapper + Anthropic tool schema
│
├── hooks/
│   └── hipaa_guardrail.py         # PreToolUse HIPAA PII scanner
│
├── utils/
│   ├── logger.py                   # Structured logging
│   ├── state.py                    # PipelineState + Pydantic models
│   └── pdf_parser.py               # PDF / .txt reader (PyMuPDF)
│
├── sample_data/
│   └── sample_patient.txt          # Realistic NSCLC patient chart with PII
│
└── tests/
    └── test_pipeline_dryrun.py     # 28 unit tests (no API key needed)
```

---

## Technical Safeguards

### HIPAA PreToolUse Guardrail
`hooks/hipaa_guardrail.py` intercepts every `search_clinical_trials` call before it executes. If the payload contains a full name, phone number, email, SSN, or date of birth — execution is aborted immediately with a `HIPAAViolationError`. No PII ever reaches ClinicalTrials.gov.

### Context Compaction (Evaluator)
Each of the ≤20 trials is evaluated in a **completely separate Claude API call** with a fresh message history. This prevents cross-trial contamination of inclusion/exclusion reasoning and keeps per-call token usage bounded (~3–5K tokens per trial regardless of dataset size).

### Unit Normalization
The Evaluator's system prompt instructs Claude to normalize medical units before numeric comparison. `1.8 K/μL` and `1800/μL` are treated as identical, preventing false rejections from unit formatting differences.

### Graceful Degradation
- Each agent stores errors in `PipelineState.errors` rather than raising.
- Fatal errors (e.g., Anonymizer API failure) stop the pipeline and emit an error report.
- Non-fatal errors (e.g., one trial evaluation failing) let the pipeline continue.
- The Scribe has a Python fallback report that runs if its own Claude call fails.

---

## Output: report.md

The generated dossier contains:

1. **Executive Summary** — checklist of why the patient qualifies for each trial
2. **Trial Breakdown Table** — NCT ID | Official Title | Phase | Primary Location  
3. **Trial Details** — per-trial eligibility summary with bullet points
4. **Next Steps** — direct enrollment contact information table
5. **Pipeline Summary** — trials fetched / evaluated / matched / rejected

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *(required)* | Your Anthropic API key |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Model used for all agents |
| `CLINICAL_TRIALS_API_BASE_URL` | `https://clinicaltrials.gov/api/v2` | API base URL |
| `MAX_TRIALS` | `20` | Maximum trials fetched per search |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

---

## Sprint Delivery Checklist

| Requirement | Status |
|-------------|--------|
| Master Orchestrator with sequential subagent control | ✅ |
| Subagent 1: PII redaction + FHIR JSON output | ✅ |
| Subagent 2: ClinicalTrials.gov v2 tool-use loop | ✅ |
| Subagent 3: Per-trial eligibility evaluation | ✅ |
| Subagent 4: Physician Markdown dossier | ✅ |
| HIPAA PreToolUse hook (aborts on PII) | ✅ |
| Context compaction (isolated sub-turn per trial) | ✅ |
| Unit normalization instructions in Evaluator prompt | ✅ |
| Graceful exception handling with bottleneck reporting | ✅ |
| CLI: `python main.py --input chart.txt --output report.md` | ✅ |
| Sample patient chart (.txt) | ✅ |
| 28 unit tests (no API key required) | ✅ |
