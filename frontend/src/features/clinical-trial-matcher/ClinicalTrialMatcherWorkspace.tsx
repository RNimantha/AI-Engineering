import { useMemo, useState } from "react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  cleanFhirPreview,
  dossierPreview,
  matcherAgents,
  memoryEntries,
  rawChartSample,
  safeguards,
  sprintBacklog,
  trialCandidates,
} from "./clinicalTrialMatcher.data";
import "./clinicalTrialMatcher.css";

function StatusPill({ value }: { value: string }) {
  return <span className="ctm-pill">{value}</span>;
}

export function ClinicalTrialMatcherWorkspace() {
  const [selectedAgentId, setSelectedAgentId] = useState(matcherAgents[0]?.id ?? "");
  const selectedAgent = useMemo(
    () => matcherAgents.find((agent) => agent.id === selectedAgentId) ?? matcherAgents[0],
    [selectedAgentId],
  );

  return (
    <div className="ctm-shell">
      <section className="ctm-overview">
        <div className="ctm-overview-header">
          <div className="ctm-overview-copy">
            <span className="ctm-eyebrow">Automated Clinical Trial Matcher MVP</span>
            <h2>Clinical operations dashboard for chart-to-trial matching</h2>
            <p>
              Structured workspace for a Claude Agent SDK orchestrator with strict privacy guardrails and
              physician-ready reporting.
            </p>
          </div>
          <div className="ctm-overview-badges">
            <StatusPill value="Claude Agent SDK" />
            <StatusPill value="ClinicalTrials.gov API v2" />
            <StatusPill value="End-of-sprint CLI demo" />
          </div>
        </div>

        <div className="ctm-kpi-grid">
          <article className="ctm-kpi-card">
            <span>Execution model</span>
            <strong>1 orchestrator + 4 subagents</strong>
            <p>Single threaded flow with state handoff at each stage.</p>
          </article>
          <article className="ctm-kpi-card">
            <span>Primary safeguard</span>
            <strong>HIPAA PreToolUse gate</strong>
            <p>Outbound calls are blocked when redaction is incomplete.</p>
          </article>
          <article className="ctm-kpi-card">
            <span>Evaluation strategy</span>
            <strong>Per-trial isolated loop</strong>
            <p>Context compaction after every eligibility decision.</p>
          </article>
          <article className="ctm-kpi-card">
            <span>Deliverable</span>
            <strong>Markdown `report.md`</strong>
            <p>Executive checklist, trial table, and enrollment next steps.</p>
          </article>
        </div>
      </section>

      <section className="ctm-section">
        <div className="ctm-section-header">
          <div>
            <span className="ctm-section-kicker">Execution flow</span>
            <h3>Sequential orchestration chain</h3>
          </div>
          <StatusPill value="No state loss between stages" />
        </div>

        <ol className="ctm-flow-track" aria-label="Orchestration pipeline stages">
          <li className="ctm-flow-step">
            <strong>01 Intake</strong>
            <p>Load local PDF/TXT chart into `raw_payload`.</p>
          </li>
          <li className="ctm-flow-step">
            <strong>02 Redaction + Parsing</strong>
            <p>Strip PII and transform chart text to FHIR-aligned JSON.</p>
          </li>
          <li className="ctm-flow-step">
            <strong>03 Trial Retrieval</strong>
            <p>Query ClinicalTrials.gov with `query.cond` and `RECRUITING` status.</p>
          </li>
          <li className="ctm-flow-step">
            <strong>04 Eligibility Judge</strong>
            <p>Process each trial in isolated loops and reject on first exclusion mismatch.</p>
          </li>
          <li className="ctm-flow-step">
            <strong>05 Physician Dossier</strong>
            <p>Publish verified shortlist and next actions as Markdown report.</p>
          </li>
        </ol>
      </section>

      <div className="ctm-layout-two">
        <section className="ctm-section">
          <div className="ctm-section-header">
            <div>
              <span className="ctm-section-kicker">Input intake</span>
              <h3>Raw chart ingestion and privacy gate</h3>
            </div>
            <StatusPill value="PDF / TXT" />
          </div>

          <div className="ctm-upload-row">
            <div>
              <strong>Sample local chart loaded</strong>
              <p>Ready for CLI handoff to the orchestrator entrypoint.</p>
            </div>
            <button className="ctm-secondary-btn" type="button">
              Attach chart
            </button>
          </div>

          <pre className="ctm-code-block">{rawChartSample}</pre>

          <div className="ctm-warning">
            <span className="ctm-warning-tag">HIPAA guardrail</span>
            <p>Abort API calls when unredacted name or phone patterns remain in outbound payload.</p>
          </div>
        </section>

        <section className="ctm-section">
          <div className="ctm-section-header">
            <div>
              <span className="ctm-section-kicker">Shared memory</span>
              <h3>Centralized state dictionary</h3>
            </div>
            <StatusPill value="4 payload keys" />
          </div>

          <div className="ctm-memory-grid">
            {memoryEntries.map((entry) => (
              <article key={entry.key} className="ctm-memory-card">
                <div className="ctm-memory-head">
                  <code>{entry.key}</code>
                  <span className={`ctm-memory-status ctm-memory-status--${entry.status}`}>{entry.status}</span>
                </div>
                <strong>{entry.label}</strong>
                <p>{entry.preview}</p>
              </article>
            ))}
          </div>

          <div className="ctm-fhir-block">
            <div className="ctm-fhir-head">
              <strong>FHIR-aligned redaction output</strong>
              <StatusPill value="Post-redaction" />
            </div>
            <pre className="ctm-code-block ctm-code-block--compact">{cleanFhirPreview}</pre>
          </div>
        </section>
      </div>

      <section className="ctm-section">
        <div className="ctm-section-header">
          <div>
            <span className="ctm-section-kicker">Agent console</span>
            <h3>Master orchestrator and specialized subagents</h3>
          </div>
          <StatusPill value="Sequential with exception handling" />
        </div>

        <div className="ctm-agent-workspace">
          <div className="ctm-agent-list" role="tablist" aria-label="Clinical trial matcher agents">
            {matcherAgents.map((agent) => {
              const isActive = agent.id === selectedAgent.id;

              return (
                <button
                  key={agent.id}
                  className={`ctm-agent-item ctm-agent-item--${agent.status}${isActive ? " is-active" : ""}`}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  onClick={() => setSelectedAgentId(agent.id)}
                >
                  <div className="ctm-agent-item-top">
                    <span className="ctm-agent-badge">{agent.badge}</span>
                    <span className="ctm-agent-role">{agent.subtitle}</span>
                  </div>
                  <strong>{agent.title}</strong>
                  <p>{agent.summary}</p>
                </button>
              );
            })}
          </div>

          <div className="ctm-agent-detail" role="tabpanel">
            <div className="ctm-agent-detail-header">
              <div>
                <span className="ctm-section-kicker">{selectedAgent.badge}</span>
                <h4>{selectedAgent.title}</h4>
              </div>
              <StatusPill value={selectedAgent.subtitle} />
            </div>

            <p className="ctm-agent-user-story">{selectedAgent.userStory}</p>

            <div className="ctm-agent-io">
              <article>
                <span>Input</span>
                <p>{selectedAgent.input}</p>
              </article>
              <article>
                <span>Output</span>
                <p>{selectedAgent.output}</p>
              </article>
            </div>

            <div className="ctm-agent-lists">
              <div>
                <span className="ctm-list-label">Processing steps</span>
                <ul>
                  {selectedAgent.processingSteps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ul>
              </div>
              <div>
                <span className="ctm-list-label">Acceptance criteria</span>
                <ul>
                  {selectedAgent.acceptanceCriteria.map((criterion) => (
                    <li key={criterion}>{criterion}</li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="ctm-agent-meta-grid">
              <article>
                <span className="ctm-list-label">Tooling</span>
                <p>{selectedAgent.tool ?? "Claude Agent SDK subagent execution only."}</p>
              </article>
              <article>
                <span className="ctm-list-label">Guardrail</span>
                <p>{selectedAgent.guardrail ?? "No extra guardrail beyond the shared orchestrator contract."}</p>
              </article>
            </div>
          </div>
        </div>
      </section>

      <section className="ctm-section">
        <div className="ctm-section-header">
          <div>
            <span className="ctm-section-kicker">Eligibility verdicts</span>
            <h3>Trial review queue and decisions</h3>
          </div>
          <StatusPill value="Maximum 20 candidates" />
        </div>

        <div className="ctm-results-layout">
          <div className="ctm-table-wrap">
            <table className="ctm-table">
              <thead>
                <tr>
                  <th>NCT ID</th>
                  <th>Official Title</th>
                  <th>Phase</th>
                  <th>Primary Location</th>
                  <th>Verdict</th>
                </tr>
              </thead>
              <tbody>
                {trialCandidates.map((trial) => (
                  <tr key={trial.nctId}>
                    <td>{trial.nctId}</td>
                    <td>{trial.officialTitle}</td>
                    <td>{trial.phase}</td>
                    <td>{trial.primaryLocation}</td>
                    <td>
                      <span className={`ctm-verdict ctm-verdict--${trial.status.toLowerCase()}`}>{trial.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <aside className="ctm-reason-list">
            {trialCandidates.map((trial) => (
              <article key={trial.nctId} className="ctm-reason-card">
                <div className="ctm-reason-head">
                  <strong>{trial.nctId}</strong>
                  <span className={`ctm-verdict ctm-verdict--${trial.status.toLowerCase()}`}>{trial.status}</span>
                </div>
                <p>{trial.reason}</p>
              </article>
            ))}
          </aside>
        </div>
      </section>

      <div className="ctm-layout-two">
        <section className="ctm-section">
          <div className="ctm-section-header">
            <div>
              <span className="ctm-section-kicker">Physician dossier</span>
              <h3>Markdown report preview</h3>
            </div>
            <StatusPill value="report.md" />
          </div>

          <div className="ctm-dossier">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{dossierPreview}</ReactMarkdown>
          </div>
        </section>

        <section className="ctm-section">
          <div className="ctm-section-header">
            <div>
              <span className="ctm-section-kicker">Safeguards</span>
              <h3>Technical guardrails and sprint tracks</h3>
            </div>
            <StatusPill value="Patient safety" />
          </div>

          <div className="ctm-safeguard-list">
            {safeguards.map((guardrail) => (
              <article key={guardrail.title} className="ctm-safeguard-card">
                <strong>{guardrail.title}</strong>
                <p>{guardrail.detail}</p>
                <span>{guardrail.emphasis}</span>
              </article>
            ))}
          </div>

          <div className="ctm-backlog-list">
            {sprintBacklog.map((item) => (
              <article key={item.title} className="ctm-backlog-card">
                <div className="ctm-backlog-head">
                  <strong>{item.title}</strong>
                  <span>{item.owner}</span>
                </div>
                <p>{item.story}</p>
                <ul>
                  {item.acceptance.map((criterion) => (
                    <li key={criterion}>{criterion}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
