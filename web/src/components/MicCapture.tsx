import { useState, useRef, useCallback } from 'react';
import { Mic, Square, Loader2 } from 'lucide-react';

interface MicCaptureProps {
  onTranscript: (text: string) => void;
  onAudioBlob: (blob: Blob) => void;
  isProcessing: boolean;
}

export default function MicCapture({ onTranscript, onAudioBlob, isProcessing }: MicCaptureProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      // No forced mimeType: let the browser pick its native format (Chrome=webm,
      // Safari/iOS=mp4). The backend transcodes whatever it receives to WAV for Gemini.
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        // Single reliable path: hand the recorded blob to the parent, which POSTs it to
        // /api/transcribe (Gemini STT; backend transcodes to WAV). No Web Speech API — it
        // can't transcribe a recorded blob and was racing/duplicating the agent call.
        const blob = new Blob(chunksRef.current, {
          type: mediaRecorder.mimeType || 'audio/webm',
        });
        onAudioBlob(blob);
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      timerRef.current = setInterval(() => {
        setRecordingTime((t) => t + 1);
      }, 1000);
    } catch (err) {
      console.error('Failed to start recording:', err);
      alert('Microphone access denied. Please allow microphone access.');
    }
  }, [onTranscript, onAudioBlob]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      if (timerRef.current) clearInterval(timerRef.current);
      setIsRecording(false);
      // Stop all tracks
      streamRef.current?.getTracks().forEach((t) => t.stop());
    }
  }, [isRecording]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-col items-center gap-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">What can we help you with?</h2>
        <p className="text-gray-600">Tap the microphone and describe your complaint</p>
      </div>

      <button
        onClick={isRecording ? stopRecording : startRecording}
        disabled={isProcessing}
        className={`mic-button ${isRecording ? 'recording' : ''}`}
      >
        {isProcessing ? (
          <Loader2 className="w-8 h-8 animate-spin" />
        ) : isRecording ? (
          <Square className="w-8 h-8" />
        ) : (
          <Mic className="w-8 h-8" />
        )}
      </button>

      {isRecording && (
        <div className="text-center">
          <p className="text-red-500 font-semibold animate-pulse">Recording...</p>
          <p className="text-gray-500 text-sm">{formatTime(recordingTime)}</p>
          <p className="text-gray-400 text-xs mt-1">Tap again to stop</p>
        </div>
      )}

      {!isRecording && !isProcessing && (
        <p className="text-gray-400 text-sm">Tap to start recording</p>
      )}

      {isProcessing && (
        <div className="text-center">
          <p className="text-nyc-blue font-semibold">Processing your complaint...</p>
          <p className="text-gray-500 text-sm">Finding the right service</p>
        </div>
      )}
    </div>
  );
}

// TypeScript declarations for Web Speech API
declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition;
    webkitSpeechRecognition: typeof SpeechRecognition;
  }
}
