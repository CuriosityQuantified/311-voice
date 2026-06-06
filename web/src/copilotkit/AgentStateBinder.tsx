import { useState, useRef, useCallback } from "react";
import type { AgentState } from "./schema";
import { DEFAULT_AGENT_STATE } from "./schema";
import MatchResults from "../components/MatchResults";
import ServiceForm from "../components/ServiceForm";
import Confirmation from "../components/Confirmation";
import MicCapture from "../components/MicCapture";
import TTSPlayer from "../components/TTSPlayer";

const API_URL = "http://localhost:8000/api/agent";
const TRANSCRIBE_URL = "http://localhost:8000/api/transcribe";

interface AgentStateBinderProps {
  mockState?: AgentState;
}

export default function AgentStateBinder({ mockState }: AgentStateBinderProps) {
  const threadId = useRef(crypto.randomUUID());
  const [state, setState] = useState<AgentState>(mockState || DEFAULT_AGENT_STATE);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const sendToAgent = useCallback(async (text: string) => {
    setIsLoading(true);
    setError("");
    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, thread_id: threadId.current }),
      });
      if (!res.ok) {
        throw new Error(`Agent error: ${res.status}`);
      }
      const newState = await res.json() as AgentState;
      setState(newState);
    } catch (err) {
      console.error("Agent request failed:", err);
      setError(err instanceof Error ? err.message : "Failed to reach agent");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleAudioBlob = useCallback(async (blob: Blob) => {
    // Send audio to backend STT, then send transcript to agent
    setIsLoading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("audio", blob);
      const res = await fetch(TRANSCRIBE_URL, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        throw new Error(`STT error: ${res.status}`);
      }
      const data = await res.json();
      const text = data.text || "";
      if (text) {
        await sendToAgent(text);
      } else {
        setError("Could not transcribe audio. Please try again.");
      }
    } catch (err) {
      console.error("STT request failed:", err);
      setError(err instanceof Error ? err.message : "Failed to transcribe audio");
    } finally {
      setIsLoading(false);
    }
  }, [sendToAgent]);

  const handleTranscript = useCallback(async (text: string) => {
    if (text) {
      await sendToAgent(text);
    }
  }, [sendToAgent]);

  const screen = state.screen || "mic";

  return (
    <div className="w-full h-full flex flex-col">
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 max-w-sm w-full">
          <span className="text-red-500 text-xs">{error}</span>
        </div>
      )}

      {/* Agent reply text + TTS audio */}
      {state.reply && screen !== "mic" && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg max-w-sm w-full">
          <p className="text-blue-800 text-sm font-medium mb-2">{state.reply}</p>
          <TTSPlayer text={state.reply} autoPlay={true} />
        </div>
      )}

      {isLoading && screen !== "mic" && (
        <div className="absolute inset-0 bg-white/80 flex items-center justify-center z-50">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-nyc-blue border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-nyc-blue font-semibold text-sm">Agent is thinking...</p>
          </div>
        </div>
      )}

      {screen === "mic" && (
        <MicCapture
          onTranscript={handleTranscript}
          onAudioBlob={handleAudioBlob}
          isProcessing={isLoading}
        />
      )}

      {screen === "results" && (
        <MatchResults
          candidates={state.candidates || []}
          pickedKa={state.picked_ka || ""}
          onContinue={() => sendToAgent("Continue to the form")}
          onBack={() => sendToAgent("Go back to mic")}
        />
      )}

      {screen === "form" && (
        <ServiceForm
          pickedKa={state.form?.ka || state.picked_ka || ""}
          kaTitle={state.candidates?.find(c => c.ka === (state.form?.ka || state.picked_ka))?.title || ""}
          formData={state.form || DEFAULT_AGENT_STATE.form}
          onSubmit={() => sendToAgent("Submit the form")}
          onBack={() => sendToAgent("Go back to results")}
          isSubmitting={isLoading}
          onFieldTranscript={(field, transcript) => {
            sendToAgent(`Update the ${field} field: ${transcript}`);
          }}
          onGeneralTranscript={(transcript) => {
            sendToAgent(`General modification: ${transcript}`);
          }}
        />
      )}

      {screen === "confirm" && (
        <Confirmation
          result={{
            sr_number: state.submission?.sr_number || "",
            payload: state.submission?.payload as any || {},
            status: state.submission?.status || "",
          }}
          onReset={() => {
            setState(DEFAULT_AGENT_STATE);
            threadId.current = crypto.randomUUID();
          }}
        />
      )}
    </div>
  );
}
