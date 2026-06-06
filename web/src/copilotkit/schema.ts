// =============================================================================
// SHARED SCHEMA: CopilotKit useAgent Shared-State Contract
// =============================================================================
// Single source of truth for the data shape shared between the backend agent
// (LangChain + CopilotKit runtime) and the frontend (useAgent hook).
//
// BOTH Hermes (frontend) and Claude (backend) must stay in sync with this file.
// If you change this, update both the agent state definition AND the UI bindings.
// =============================================================================

// ---------------------------------------------------------------------------
// Agent State (returned by useAgent)
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
}

// ---------------------------------------------------------------------------
// Agent Tool Names (backend-defined, in app/agent.py)
// ---------------------------------------------------------------------------
// The agent calls these tools to mutate state:
//   - search_services(text)       → sets candidates, screen="results"
//   - recommend_service(picked_ka, reasoning) → sets picked_ka, reasoning, emergency
//   - update_form(ka?, description?, address?, borough?, apartment?, locationDetails?) → partial update
//   - submit_service_request()    → sets submission, screen="confirm"
// ---------------------------------------------------------------------------

export const AGENT_TOOLS = {
  SEARCH_SERVICES: "search_services",
  RECOMMEND_SERVICE: "recommend_service",
  UPDATE_FORM: "update_form",
  SUBMIT_SERVICE_REQUEST: "submit_service_request",
} as const;

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
