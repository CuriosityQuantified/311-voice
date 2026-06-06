import { useState, useCallback } from 'react';
import { Mic, AlertCircle } from 'lucide-react';
import type { AppStep, MatchResponse, SubmitPayload, SubmitResponse } from './types';
import { matchComplaint, submitRequest } from './api';
import MicCapture from './components/MicCapture';
import MatchResults from './components/MatchResults';
import ServiceForm from './components/ServiceForm';
import Confirmation from './components/Confirmation';

export default function App() {
  const [step, setStep] = useState<AppStep>('mic');
  const [matchResult, setMatchResult] = useState<MatchResponse | null>(null);
  const [submitResult, setSubmitResult] = useState<SubmitResponse | null>(null);
  const [error, setError] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);

  const handleTranscript = useCallback(
    async (text: string) => {
      setIsProcessing(true);
      setError('');
      try {
        // If Web Speech gave us text, use it; otherwise backend will transcribe from audio
        const result = await matchComplaint(text || 'audio_upload_placeholder');
        setMatchResult(result);
        setStep('results');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to match complaint');
        setStep('mic');
      } finally {
        setIsProcessing(false);
      }
    },
    []
  );

  const handleAudioBlob = useCallback((blob: Blob) => {
    setAudioBlob(blob);
  }, []);

  const handleContinue = useCallback(() => {
    setStep('form');
  }, []);

  const handleBack = useCallback(() => {
    setStep('mic');
    setMatchResult(null);
    setError('');
  }, []);

  const handleSubmit = useCallback(
    async (payload: SubmitPayload) => {
      setIsSubmitting(true);
      setError('');
      try {
        const result = await submitRequest(payload);
        setSubmitResult(result);
        setStep('confirm');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to submit');
      } finally {
        setIsSubmitting(false);
      }
    },
    []
  );

  const handleReset = useCallback(() => {
    setStep('mic');
    setMatchResult(null);
    setSubmitResult(null);
    setError('');
    setAudioBlob(null);
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="phone-frame">
        {/* iPhone notch */}
        <div className="phone-notch" />
        
        {/* Screen content */}
        <div className="phone-screen">
          <main className="flex-1 flex flex-col items-center justify-center p-4 overflow-y-auto">
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 max-w-sm w-full">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                <p className="text-red-700 text-xs">{error}</p>
              </div>
            )}

            {step === 'mic' && (
              <MicCapture
                onTranscript={handleTranscript}
                onAudioBlob={handleAudioBlob}
                isProcessing={isProcessing}
              />
            )}

            {step === 'results' && matchResult && (
              <MatchResults
                result={matchResult}
                onContinue={handleContinue}
                onBack={handleBack}
              />
            )}

            {step === 'form' && matchResult && (
              <ServiceForm
                pickedKa={matchResult.picked_ka}
                kaTitle={
                  matchResult.candidates.find((c) => c.ka === matchResult.picked_ka)
                    ?.title || 'Unknown Service'
                }
                extractedFields={matchResult.extracted_fields}
                onSubmit={handleSubmit}
                onBack={handleBack}
                isSubmitting={isSubmitting}
              />
            )}

            {step === 'confirm' && submitResult && (
              <Confirmation result={submitResult} onReset={handleReset} />
            )}
          </main>

          {/* Footer */}
          <footer className="bg-gray-100 py-2 px-4 text-center flex-shrink-0">
            <p className="text-[10px] text-gray-500">
              Hackathon Demo · Mock Submission Only
            </p>
          </footer>
        </div>
        
        {/* Home indicator */}
        <div className="phone-home-indicator" />
      </div>
    </div>
  );
}
