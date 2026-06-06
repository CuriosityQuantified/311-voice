// =============================================================================
// SHARED SCHEMA: REST Agent Shared-State Contract
// =============================================================================
// Single source of truth for the data shape shared between the backend agent
// (LangChain) and the frontend (AgentStateBinder over fetch POST /api/agent).
//
// BOTH Hermes (frontend) and Claude (backend) must stay in sync with this file.
// If you change this, update both the agent state definition AND the UI bindings.
// =============================================================================

// ---------------------------------------------------------------------------
// Agent State (returned by POST /api/agent)
// ---------------------------------------------------------------------------

export type Screen = "mic" | "results" | "form" | "confirm";

export interface FormDraft {
  ka: string;
  description: string;
  address: string;
  borough: string;
  apartment: string;
  locationDetails: string;
}

export interface Submission {
  sr_number: string;
  payload: Record<string, unknown>;
  status: string;
}

export interface MatchCandidate {
  ka: string;
  title: string;
  description: string;
  score: number;
  classification: string;
}

export interface AgentState {
  transcript: string;
  candidates: MatchCandidate[];
  picked_ka: string;
  reasoning: string;
  emergency: boolean;
  form: FormDraft;
  submission: Submission;
  screen: Screen;
  reply?: string;              // Agent's natural-language message to display
  todos?: Array<{content: string; status: string}>; // Agent internal todo list
}

// ---------------------------------------------------------------------------
// Default / empty state
// ---------------------------------------------------------------------------
export const DEFAULT_FORM: FormDraft = {
  ka: "",
  description: "",
  address: "",
  borough: "",
  apartment: "",
  locationDetails: "",
};

export const DEFAULT_SUBMISSION: Submission = {
  sr_number: "",
  payload: {},
  status: "",
};

export const DEFAULT_AGENT_STATE: AgentState = {
  transcript: "",
  candidates: [],
  picked_ka: "",
  reasoning: "",
  emergency: false,
  form: DEFAULT_FORM,
  submission: DEFAULT_SUBMISSION,
  screen: "mic",
};
