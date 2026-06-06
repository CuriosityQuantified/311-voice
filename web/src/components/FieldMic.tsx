import { useState, useRef, useCallback } from 'react';
import { Mic, Square, Loader2 } from 'lucide-react';

interface FieldMicProps {
  onTranscript: (text: string) => void;
  size?: 'sm' | 'md';
}

export default function FieldMic({ onTranscript, size = 'sm' }: FieldMicProps) {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      const chunks: Blob[] = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };

      mediaRecorder.onstop = () => {
        // Try Web Speech API for immediate transcript
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
          const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
          const recognition = new SpeechRecognition();
          recognition.continuous = false;
          recognition.interimResults = false;
          recognition.lang = 'en-US';
          recognition.onresult = (event: SpeechRecognitionEvent) => {
            const text = event.results[0][0].transcript;
            onTranscript(text);
          };
          recognition.onerror = () => {
            onTranscript('');
          };
          recognition.start();
        } else {
          onTranscript('');
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error('Failed to start recording:', err);
    }
  }, [onTranscript]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      streamRef.current?.getTracks().forEach((t) => t.stop());
    }
  }, [isRecording]);

  const iconSize = size === 'sm' ? 'w-4 h-4' : 'w-6 h-6';
  const buttonSize = size === 'sm' ? 'w-8 h-8' : 'w-12 h-12';

  return (
    <button
      type="button"
      onClick={isRecording ? stopRecording : startRecording}
      className={`${buttonSize} rounded-full flex items-center justify-center transition-all ${
        isRecording
          ? 'bg-red-500 text-white animate-pulse'
          : 'bg-nyc-blue text-white hover:bg-blue-700'
      }`}
      title={isRecording ? 'Tap to stop recording' : 'Tap to speak'}
    >
      {isRecording ? (
        <Square className={`${iconSize}`} />
      ) : (
        <Mic className={`${iconSize}`} />
      )}
    </button>
  );
}

// TypeScript declarations for Web Speech API
declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition;
    webkitSpeechRecognition: typeof SpeechRecognition;
  }
}
