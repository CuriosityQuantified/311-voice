import { useCopilotAction } from "@copilotkit/react-core";
import MatchResults from "../components/MatchResults";

export default function MatchResultsAction() {
  useCopilotAction({
    name: "show_match_results",
    description: "Display the match results for the user's complaint. Show the top picked service and other candidate matches.",
    parameters: [
      { name: "picked_ka", type: "string", description: "The KA number of the top matched service" },
      { name: "picked_title", type: "string", description: "Title of the top matched service" },
      { name: "picked_description", type: "string", description: "Description of the top matched service" },
      { name: "other_matches", type: "string", description: "JSON array of other candidate matches with ka, title, description" },
    ],
    handler: async () => {
      // The handler is required by useCopilotAction but rendering is done via render prop
      return "Match results displayed";
    },
    render: ({ status, args }) => {
      const picked = {
        ka: args.picked_ka || "KA-00000",
        title: args.picked_title || "Unknown Service",
        description: args.picked_description || "",
        score: 1.0,
        classification: "submittable",
      };

      let others: Array<{ ka: string; title: string; description: string; score: number; classification: string }> = [];
      try {
        others = JSON.parse(args.other_matches || "[]");
      } catch {
        others = [];
      }

      const candidates = [picked, ...others];

      const result = {
        candidates,
        picked_ka: picked.ka,
        reasoning: "",
        extracted_fields: { description: "", address: "", apartment: "", locationDetails: "" },
      };

      if (status === "executing") {
        return (
          <div className="flex items-center gap-2 text-nyc-blue">
            <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">Finding the right service...</span>
          </div>
        );
      }

      return (
        <MatchResults
          result={result}
          onContinue={() => {
            // The agent will continue to the form step
            window.dispatchEvent(new CustomEvent("copilotkit:continue_to_form"));
          }}
          onBack={() => {
            window.dispatchEvent(new CustomEvent("copilotkit:go_back_to_mic"));
          }}
        />
      );
    },
  });

  return null;
}
