import { HashRouter, Routes, Route } from 'react-router-dom';
import App from './App';
import MicCapture from './components/MicCapture';
import MatchResults from './components/MatchResults';
import ServiceForm from './components/ServiceForm';
import Confirmation from './components/Confirmation';
import type { MatchResponse, SubmitResponse } from './types';

const mockMatchResult: MatchResponse = {
  candidates: [
    {
      ka: 'KA-01036',
      title: 'Heat or Hot Water Complaint in a Residential Building',
      description: 'Report heat or hot water problems in a residential building.',
      score: 0.95,
      classification: 'submittable',
    },
    {
      ka: 'KA-01017',
      title: 'Noise from Neighbor',
      description: 'Report noise from a neighbor.',
      score: 0.72,
      classification: 'submittable',
    },
    {
      ka: 'KA-01093',
      title: 'Pothole or Cave-In on Street',
      description: 'Report a pothole or cave-in on a street.',
      score: 0.68,
      classification: 'submittable',
    },
    {
      ka: 'KA-01107',
      title: 'Rat or Mouse Complaint',
      description: 'Report a rat or mouse sighting.',
      score: 0.45,
      classification: 'submittable',
    },
    {
      ka: 'KA-01084',
      title: 'Catch Basin Complaint',
      description: 'Report a clogged or broken catch basin.',
      score: 0.32,
      classification: 'submittable',
    },
  ],
  picked_ka: 'KA-01036',
  reasoning: 'The complaint explicitly mentions "no heat in my apartment," which directly matches the Heat or Hot Water service.',
  extracted_fields: {
    description: 'No heat in my apartment for the last 3 days',
    address: '123 Main St',
    apartment: '4B',
    locationDetails: '',
  },
};

const mockSubmitResult: SubmitResponse = {
  sr_number: 'SR-2026-0615-0042',
  payload: {
    ka: 'KA-01036',
    description: 'No heat in my apartment for the last 3 days',
    address: '123 Main St',
    borough: 'MANHATTAN',
    apartment: '4B',
    locationDetails: '',
    photo_b64: undefined,
  },
  status: 'mock-submitted',
};

function PreviewWrapper({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="phone-frame">
        <div className="phone-notch" />
        <div className="phone-screen">
          <header className="bg-nyc-dark text-white py-3 px-4 flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-nyc-orange rounded-lg flex items-center justify-center">
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/></svg>
              </div>
              <div>
                <h1 className="font-bold text-base">311 Voice</h1>
                <p className="text-[10px] text-gray-400">NYC 311 · Voice-Powered</p>
              </div>
            </div>
          </header>
          <main className="flex-1 flex flex-col items-center justify-center p-4 overflow-y-auto">
            {children}
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

function MicPreview() {
  return (
    <PreviewWrapper>
      <MicCapture
        onTranscript={() => {}}
        onAudioBlob={() => {}}
        isProcessing={false}
      />
    </PreviewWrapper>
  );
}

function ResultsPreview() {
  return (
    <PreviewWrapper>
      <MatchResults
        result={mockMatchResult}
        onContinue={() => alert('Would go to form')}
        onBack={() => alert('Would go back to mic')}
      />
    </PreviewWrapper>
  );
}

function FormPreview() {
  return (
    <PreviewWrapper>
      <ServiceForm
        pickedKa="KA-01036"
        kaTitle="Heat or Hot Water Complaint in a Residential Building"
        extractedFields={mockMatchResult.extracted_fields}
        onSubmit={() => alert('Would submit')}
        onBack={() => alert('Would go back')}
        isSubmitting={false}
      />
    </PreviewWrapper>
  );
}

function ConfirmPreview() {
  return (
    <PreviewWrapper>
      <Confirmation result={mockSubmitResult} onReset={() => alert('Would reset')} />
    </PreviewWrapper>
  );
}

export default function Preview() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/mic" element={<MicPreview />} />
        <Route path="/results" element={<ResultsPreview />} />
        <Route path="/form" element={<FormPreview />} />
        <Route path="/confirm" element={<ConfirmPreview />} />
      </Routes>
    </HashRouter>
  );
}
