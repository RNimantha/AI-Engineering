export type AgentStatus = "orchestrating" | "guarded" | "querying" | "sequential" | "reporting";

export type MatcherAgent = {
  id: string;
  badge: string;
  title: string;
  subtitle: string;
  summary: string;
  input: string;
  output: string;
  userStory: string;
  tool?: string;
  guardrail?: string;
  acceptanceCriteria: string[];
  processingSteps: string[];
  status: AgentStatus;
};

export type MemoryEntry = {
  key: string;
  label: string;
  status: "ready" | "pending";
  preview: string;
};

export type TrialCandidate = {
  nctId: string;
  officialTitle: string;
  phase: string;
  primaryLocation: string;
  status: "Verified" | "Rejected" | "Review";
  reason: string;
};

export type Safeguard = {
  title: string;
  detail: string;
  emphasis: string;
};

export type SprintCard = {
  title: string;
  owner: string;
  story: string;
  acceptance: string[];
};
