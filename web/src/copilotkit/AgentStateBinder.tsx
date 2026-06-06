import { useCoAgent } from "@copilotkit/react-core";
import { useState, useEffect } from "react";
import type { AgentState, Screen } from "./schema";
import { DEFAULT_AGENT_STATE } from "./schema";
import MatchResults from "../components/MatchResults";
import ServiceForm from "../components/ServiceForm";
import Confirmation from "../components/Confirmation";
import MicCapture from "../components/MicCapture";

interface AgentStateBinderProps {
  mockState?: AgentState;
}

export default function AgentStateBinder({ mockState }: AgentStateBinderProps) {
  const agent = useCoAgent<AgentState>({
    name: "threeoneone",
    initialState: mockState || DEFAULT_AGENT_STATE,
  });
  const state = agent.state || mockState || DEFAULT_AGENT_STATE;
  const [screen, setScreen] = useState<Screen>(state.screen || "mic");

  useEffect(() => {
    if (state.screen) {
      setScreen(state.screen);
    }
  }, [state.screen]);

  // Send a message to the agent (e.g., when user clicks Continue)
  const sendMessage = (text: string) => {
    if (agent.run) {
      agent.run(text);
    }
  };

  // Render the correct screen based on state
  if (screen === "mic") {
    return (
      <MicCapture
        onTranscript={() => {}}
        onAudioBlob={() => {}}
        isProcessing={false}
      />
    );
  }

  if (screen === "results") {
    return (
      <MatchResults
        candidates={state.candidates || []}
        pickedKa={state.picked_ka || ""}
        onContinue={() => sendMessage("Yes, that's the right service. My address is ")}
        onBack={() => sendMessage("No, that's not right. Let me try again.")}
      />
    );
  }

  if (screen === "form") {
    const formKa = state.form?.ka || state.picked_ka || "";
    const kaTitle = state.candidates?.find(c => c.ka === formKa)?.title || "";
    return (
      <ServiceForm
        pickedKa={formKa}
        kaTitle={kaTitle}
        formData={state.form || DEFAULT_AGENT_STATE.form}
        onSubmit={(payload) => {
          sendMessage(`Submitting: ${JSON.stringify(payload)}`);
        }}
        onBack={() => sendMessage("Go back to the results.")}
        isSubmitting={false}
        onFieldTranscript={(field, transcript) => {
          sendMessage(`Update the ${field} field: ${transcript}`);
        }}
        onGeneralTranscript={(transcript) => {
          sendMessage(`General modification: ${transcript}`);
        }}
      />
    );
  }

  if (screen === "confirm") {
    return (
      <Confirmation
        result={{
          sr_number: state.submission?.sr_number || "SR-2026-0615-0042",
          payload: state.submission?.payload as any || {},
          status: state.submission?.status || "mock-submitted",
        }}
        onReset={() => sendMessage("Start a new complaint.")}
      />
    );
  }

  return null;
}
