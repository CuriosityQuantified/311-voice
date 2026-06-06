import { useCopilotAction } from "@copilotkit/react-core";
import ServiceForm from "../components/ServiceForm";

export default function ServiceFormAction() {
  useCopilotAction({
    name: "show_service_form",
    description: "Display the service request form for the user to fill out address, borough, and other details.",
    parameters: [
      { name: "ka", type: "string", description: "The KA number of the selected service" },
      { name: "ka_title", type: "string", description: "Title of the selected service" },
      { name: "description", type: "string", description: "Pre-filled description from the complaint" },
      { name: "address", type: "string", description: "Pre-filled address if available" },
      { name: "apartment", type: "string", description: "Pre-filled apartment number if available" },
      { name: "location_details", type: "string", description: "Pre-filled location details if available" },
    ],
    handler: async () => {
      return "Service form displayed";
    },
    render: ({ status, args }) => {
      const extractedFields = {
        description: args.description || "",
        address: args.address || "",
        apartment: args.apartment || "",
        locationDetails: args.location_details || "",
      };

      if (status === "executing") {
        return (
          <div className="flex items-center gap-2 text-nyc-blue">
            <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">Preparing the form...</span>
          </div>
        );
      }

      return (
        <ServiceForm
          pickedKa={args.ka || "KA-00000"}
          kaTitle={args.ka_title || "Unknown Service"}
          extractedFields={extractedFields}
          onSubmit={(payload) => {
            window.dispatchEvent(
              new CustomEvent("copilotkit:form_submitted", {
                detail: payload,
              })
            );
          }}
          onBack={() => {
            window.dispatchEvent(new CustomEvent("copilotkit:go_back_to_results"));
          }}
          isSubmitting={false}
        />
      );
    },
  });

  return null;
}
