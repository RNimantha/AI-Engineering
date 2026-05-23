import type { MatcherAgent, MemoryEntry, Safeguard, SprintCard, TrialCandidate } from "./clinicalTrialMatcher.types";

export const rawChartSample = `Patient Name: Maria Johnson
DOB: 1991-04-18
Phone: (312) 555-0188
Email: maria.johnson@example.org
ZIP: 60611

Assessment:
- Metastatic triple-negative breast cancer with hepatic lesions.
- ECOG 1. Prior pembrolizumab exposure ended 8 months ago.

Current medications:
- Capecitabine
- Zoledronic acid

Recent labs:
- ANC 1.8 K/uL
- Platelets 182 K/uL
- Hemoglobin 11.2 g/dL
- AST 28 U/L
- ALT 31 U/L`;

export const cleanFhirPreview = `{
  "resourceType": "Bundle",
  "patient_profile": {
    "age_range": "32 years old",
    "sex": "female",
    "performance_status": "ECOG 1"
  },
  "conditions": [
    "metastatic triple-negative breast cancer",
    "hepatic lesions"
  ],
  "medications": [
    "capecitabine",
    "zoledronic acid"
  ],
  "lab_results": [
    { "name": "ANC", "value": 1.8, "unit": "K/uL" },
    { "name": "Platelets", "value": 182, "unit": "K/uL" },
    { "name": "AST", "value": 28, "unit": "U/L" }
  ]
}`;

export const memoryEntries: MemoryEntry[] = [
  {
    key: "raw_payload",
    label: "Raw chart payload",
    status: "ready",
    preview: "Loaded from local .txt or PDF before orchestration begins.",
  },
  {
    key: "clean_fhir_json",
    label: "Structured FHIR JSON",
    status: "ready",
    preview: "Redacted conditions, medications, labs, and normalized patient profile.",
  },
  {
    key: "candidate_trials_raw",
    label: "ClinicalTrials.gov candidate set",
    status: "ready",
    preview: "RECRUITING trial array capped at 20 records with nctId, title, eligibility, locations.",
  },
  {
    key: "verified_matches",
    label: "Physician-ready verified matches",
    status: "ready",
    preview: "Only trials that survive line-by-line eligibility evaluation reach the dossier.",
  },
];

export const matcherAgents: MatcherAgent[] = [
  {
    id: "orchestrator",
    badge: "Master",
    title: "Master Orchestrator",
    subtitle: "Command center",
    summary: "Initializes `claude_agent_sdk.query`, moves shared state forward, and traps downstream errors.",
    input: "Raw chart payload plus centralized memory dictionary.",
    output: "Sequential lifecycle control with bottleneck reporting and resilient state handoff.",
    userStory:
      "As a system router, I need to coordinate the lifecycle of the subagents so that data flows sequentially without state loss.",
    guardrail: "Catches timeouts, preserves the current state snapshot, and reports the failing stage without crashing.",
    acceptanceCriteria: [
      "Initialize the master loop with `claude_agent_sdk.query`.",
      "Maintain `raw_payload`, `clean_fhir_json`, `candidate_trials_raw`, and `verified_matches`.",
      "Catch downstream exceptions and report the bottleneck cleanly.",
    ],
    processingSteps: [
      "Receive local TXT or PDF chart.",
      "Dispatch redaction and parsing.",
      "Pass compact FHIR state to API search.",
      "Loop each trial through isolated evaluation turns.",
      "Hand verified output to the dossier writer.",
    ],
    status: "orchestrating",
  },
  {
    id: "anonymizer",
    badge: "Agent 1",
    title: "Privacy Guard & Parser",
    subtitle: "Anonymizer",
    summary: "Strips identifiers before network access and reshapes messy chart text into simplified HL7 FHIR-aligned JSON.",
    input: "Raw medical chart text or markdown.",
    output: "Redacted FHIR JSON with conditions, medications, and lab_results arrays.",
    userStory:
      "As a compliance officer, I need to strip all personal identifying data before any external network requests occur.",
    guardrail: "Names, phone numbers, emails, and ZIP codes are redacted; DOB becomes an age-range field.",
    acceptanceCriteria: [
      "Scan and redact PII before any external request.",
      "Convert birthdates into generalized age wording.",
      "Return FHIR-aligned JSON with distinct clinical arrays.",
    ],
    processingSteps: [
      "Detect names and direct identifiers.",
      "Mask contact details and ZIP codes.",
      "Normalize condition, medication, and lab blocks.",
    ],
    status: "guarded",
  },
  {
    id: "searcher",
    badge: "Agent 2",
    title: "API Query Extractor",
    subtitle: "Searcher",
    summary: "Builds `query.cond` from the primary condition and calls a custom Python tool over ClinicalTrials.gov API v2.",
    input: "Cleaned FHIR JSON from Agent 1.",
    output: "Up to 20 RECRUITING raw trial objects trimmed to required fields.",
    userStory:
      "As a data engineer, I need to turn the patient's profile into programmatic queries to fetch active global trials.",
    tool: "Custom Python wrapper for ClinicalTrials.gov API v2.",
    acceptanceCriteria: [
      "Extract the primary condition and map it to `query.cond`.",
      "Force recruitment status to `RECRUITING`.",
      "Return at most 20 trials with `nctId`, `officialTitle`, `eligibilityCriteria`, and `locations`.",
    ],
    processingSteps: [
      "Read the dominant diagnosis from FHIR conditions.",
      "Assemble the API payload.",
      "Trim the response to the MVP field set.",
    ],
    status: "querying",
  },
  {
    id: "evaluator",
    badge: "Agent 3",
    title: "Eligibility Match Judge",
    subtitle: "Critic",
    summary: "Evaluates one trial at a time, normalizes units, and rejects immediately on the first exclusion mismatch.",
    input: "Cleaned FHIR JSON and the raw trial array.",
    output: "Rejected trials with one-sentence reasons plus `verified_matches` for passing trials.",
    userStory:
      "As a research nurse, I need to evaluate patient data against strict inclusion/exclusion rules to prevent dangerous mismatches.",
    guardrail: "Each trial runs in an isolated turn to compact context before the next eligibility check.",
    acceptanceCriteria: [
      "Loop sequentially over each trial object.",
      "Prompt Claude to compare labs and contraindications line by line.",
      "Reject on the first exclusion failure with a concise reason.",
    ],
    processingSteps: [
      "Normalize lab units before comparison.",
      "Check inclusion criteria.",
      "Check exclusion criteria and stop on first failure.",
      "Append pass/fail verdict to shared memory.",
    ],
    status: "sequential",
  },
  {
    id: "scribe",
    badge: "Agent 4",
    title: "Clinical Dossier Writer",
    subtitle: "Scribe",
    summary: "Transforms `verified_matches` into a physician-facing Markdown brief that can be handed off immediately.",
    input: "Verified matches from Agent 3.",
    output: "Markdown dossier with executive summary, trial table, and direct contact next steps.",
    userStory:
      "As a practicing physician, I need a highly scannable, clean summary of options so I can make an immediate clinical decision.",
    acceptanceCriteria: [
      "Generate an executive summary checklist of fit reasons.",
      "Render a trial breakdown table with NCT ID, title, phase, and primary location.",
      "Include direct enrollment contact next steps.",
    ],
    processingSteps: [
      "Summarize qualification signals.",
      "Tabulate final options.",
      "Package outreach details for the care team.",
    ],
    status: "reporting",
  },
];

export const trialCandidates: TrialCandidate[] = [
  {
    nctId: "NCT05821491",
    officialTitle: "Pembrolizumab Plus Antibody-Drug Conjugate in Metastatic Triple-Negative Breast Cancer",
    phase: "Phase 2",
    primaryLocation: "Houston, TX",
    status: "Verified",
    reason: "All reviewed inclusion markers fit and no written exclusion rule was triggered.",
  },
  {
    nctId: "NCT06104422",
    officialTitle: "Global Study of Novel TROP2 Therapy for Advanced Breast Cancer",
    phase: "Phase 1/2",
    primaryLocation: "Barcelona, Spain",
    status: "Review",
    reason: "Core profile aligns, but prior immunotherapy washout wording needs physician review.",
  },
  {
    nctId: "NCT05588230",
    officialTitle: "Targeted Combination Therapy for Heavily Pretreated Solid Tumors",
    phase: "Phase 2",
    primaryLocation: "Chicago, IL",
    status: "Rejected",
    reason: "Rejected because prior pembrolizumab exposure violates the written exclusion clause.",
  },
];

export const safeguards: Safeguard[] = [
  {
    title: "HIPAA PreToolUse hook",
    detail:
      "Abort any ClinicalTrials.gov tool call when the outbound payload still matches an unredacted name or phone-number pattern.",
    emphasis: "Mandatory before network execution.",
  },
  {
    title: "Context compaction loop",
    detail:
      "Process eligibility one trial per sub-turn so dense inclusion and exclusion text never floods the context window.",
    emphasis: "Required for all 20 trial checks.",
  },
  {
    title: "Unit normalization",
    detail:
      "Normalize medical units before reasoning so ANC, platelet, and chemistry thresholds compare cleanly against chart values.",
    emphasis: "Critical patient-safety safeguard.",
  },
];

export const sprintBacklog: SprintCard[] = [
  {
    title: "Orchestrator control loop",
    owner: "Core platform",
    story:
      "Build the sequential run controller and memory dictionary so each stage can recover gracefully from tool or model failures.",
    acceptance: [
      "Shared state survives downstream errors.",
      "Timeouts surface as explicit bottleneck notices.",
    ],
  },
  {
    title: "Anonymization and FHIR shaping",
    owner: "Compliance + NLP",
    story:
      "Redact identifiers from raw charts and map the remaining text into a simplified FHIR-aligned schema for downstream reasoning.",
    acceptance: [
      "PII is stripped before API access.",
      "Conditions, meds, and labs are separated cleanly.",
    ],
  },
  {
    title: "ClinicalTrials.gov query tool",
    owner: "Data engineering",
    story:
      "Wrap API v2 in a Python tool that enforces recruitment status and trims the response payload for the matching engine.",
    acceptance: [
      "Primary diagnosis maps to `query.cond`.",
      "Response payload is capped at 20 candidate trials.",
    ],
  },
  {
    title: "Eligibility verdict engine",
    owner: "Clinical reasoning",
    story:
      "Evaluate one trial at a time, reject immediately on exclusions, and explain failed matches in one sentence for auditability.",
    acceptance: [
      "Every rejection includes a reason string.",
      "LLM context resets between trial evaluations.",
    ],
  },
  {
    title: "Markdown dossier output",
    owner: "Physician UX",
    story:
      "Generate a scannable report that gives doctors immediate next actions instead of a raw API dump.",
    acceptance: [
      "Executive checklist is concise.",
      "Table and enrollment contacts are included in the final report.",
    ],
  },
];

export const dossierPreview = `## Executive Summary

- [x] Primary diagnosis maps to metastatic triple-negative breast cancer.
- [x] ECOG 1 performance status remains within reviewed inclusion limits.
- [x] ANC and platelet values remain above evaluated cutoffs after unit normalization.
- [x] No conflicting exclusion rule was found in the verified trial set.

## Trial Breakdown

| NCT ID | Official Title | Phase | Primary Location |
| --- | --- | --- | --- |
| NCT05821491 | Pembrolizumab Plus Antibody-Drug Conjugate in Metastatic Triple-Negative Breast Cancer | Phase 2 | Houston, TX |
| NCT06104422 | Global Study of Novel TROP2 Therapy for Advanced Breast Cancer | Phase 1/2 | Barcelona, Spain |

## Next Steps

1. Route the dossier to the treating oncologist for washout-language review on NCT06104422.
2. Contact the Houston study coordinator at \`recruitment@trialsite.org\` for screening availability.
3. Confirm latest CBC and liver panel within 7 days before submitting enrollment packets.`;
