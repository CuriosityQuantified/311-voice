// =============================================================================
// SHARED SCHEMA: CopilotKit Agent ↔ Frontend Action Contract
// =============================================================================
// This file is the single source of truth for the data shape passed between
// the backend agent (LangChain + CopilotKit runtime) and the frontend
// declarative UI components (useCopilotAction).
//
// BOTH Hermes (frontend) and Claude (backend) must stay in sync with this file.
// If you change this, update the agent tool definitions AND the render props.
// =============================================================================

// ---------------------------------------------------------------------------
// Action 1: show_match_results
// ---------------------------------------------------------------------------
// Triggered by the agent after classifying the user's voice complaint.
// Renders the MatchResults component on the frontend.

export interface ShowMatchResultsArgs {
  /** KA number of the top-picked service (e.g. "KA-01036") */
  picked_ka: string;
  /** Human-readable title of the top-picked service */
  picked_title: string;
  /** Description text for the top-picked service */
  picked_description: string;
  /**
   * JSON-stringified array of other candidate matches.
   * Each item: { ka: string, title: string, description: string }
   */
  other_matches: string;
}

// ---------------------------------------------------------------------------
// Action 2: show_service_form
// ---------------------------------------------------------------------------
// Triggered by the agent when the user confirms the match and wants to file.
// Renders the ServiceForm component on the frontend.

export interface ShowServiceFormArgs {
  /** KA number of the selected service */
  ka: string;
  /** Title of the selected service */
  ka_title: string;
  /** Pre-filled description extracted from the transcript */
  description: string;
  /** Pre-filled address if extracted from transcript or GPS */
  address: string;
  /** Pre-filled apartment/unit if extracted */
  apartment: string;
  /** Pre-filled location details if extracted */
  location_details: string;
}

// ---------------------------------------------------------------------------
// Frontend → Agent Event: form_submitted
// ---------------------------------------------------------------------------
// The frontend dispatches a CustomEvent when the user submits the form.
// The agent listens for this (or handles it via the next turn) to proceed.

export interface FormSubmittedDetail {
  ka: string;
  description: string;
  address: string;
  borough: string;
  apartment?: string;
  locationDetails?: string;
  photo_b64?: string;
}

// ---------------------------------------------------------------------------
// Frontend → Agent Event: continue_to_form
// ---------------------------------------------------------------------------
// Dispatched when the user clicks "Continue" on the match results screen.
// Tells the agent to proceed to the form step.

// export type ContinueToFormDetail = void;

// ---------------------------------------------------------------------------
// Frontend → Agent Event: go_back_to_mic
// ---------------------------------------------------------------------------
// Dispatched when the user clicks "Try Again" on the match results screen.

// export type GoBackToMicDetail = void;

// ---------------------------------------------------------------------------
// Frontend → Agent Event: go_back_to_results
// ---------------------------------------------------------------------------
// Dispatched when the user clicks "Back" on the service form screen.

// export type GoBackToResultsDetail = void;

// ---------------------------------------------------------------------------
// Agent Tool Names (must match useCopilotAction name exactly)
// ---------------------------------------------------------------------------
export const AGENT_TOOL_NAMES = {
  SHOW_MATCH_RESULTS: "show_match_results",
  SHOW_SERVICE_FORM: "show_service_form",
} as const;

// ---------------------------------------------------------------------------
// CustomEvent Names (must match window.dispatchEvent type exactly)
// ---------------------------------------------------------------------------
export const CUSTOM_EVENTS = {
  CONTINUE_TO_FORM: "copilotkit:continue_to_form",
  GO_BACK_TO_MIC: "copilotkit:go_back_to_mic",
  GO_BACK_TO_RESULTS: "copilotkit:go_back_to_results",
  FORM_SUBMITTED: "copilotkit:form_submitted",
} as const;
