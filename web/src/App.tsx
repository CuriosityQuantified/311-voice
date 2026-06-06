import AgentStateBinder from './copilotkit/AgentStateBinder';

export default function App() {
  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="phone-frame">
        <div className="phone-notch" />
        <div className="phone-screen">
          <main className="flex-1 flex flex-col items-center justify-start p-4 overflow-y-auto">
            <AgentStateBinder />
          </main>
          <footer className="bg-gray-100 py-2 px-4 text-center flex-shrink-0">
            <p className="text-[10px] text-gray-500">
              Hackathon Demo · Mock Submission Only
            </p>
          </footer>
        </div>
        <div className="phone-home-indicator" />
      </div>
    </div>
  );
}
