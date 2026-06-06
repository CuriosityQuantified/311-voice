import { useEffect, useRef } from "react";

const TTS_URL = "http://localhost:8000/api/tts";

interface TTSPlayerProps {
  text: string;
  autoPlay?: boolean;
  voice?: string;
}

/**
 * TTS Player using Gemini 3.1 Flash TTS Preview.
 * Automatically fetches WAV audio from the backend and plays it.
 * Memoizes audio per text to avoid re-fetching.
 */
export default function TTSPlayer({ text, autoPlay = true, voice = "Aoede" }: TTSPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const lastTextRef = useRef<string>("");

  useEffect(() => {
    if (!text || text === lastTextRef.current) {
      return;
    }
    lastTextRef.current = text;

    // Fetch TTS audio
    const fetchAudio = async () => {
      try {
        const res = await fetch(TTS_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, voice }),
        });
        if (!res.ok) {
          console.error("TTS fetch failed:", res.status);
          return;
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        audioUrlRef.current = url;

        if (audioRef.current) {
          audioRef.current.src = url;
          if (autoPlay) {
            audioRef.current.play().catch(() => {
              // Autoplay blocked — user will need to interact first
            });
          }
        }
      } catch (err) {
        console.error("TTS error:", err);
      }
    };

    fetchAudio();

    return () => {
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = null;
      }
    };
  }, [text, autoPlay, voice]);

  return (
    <audio
      ref={audioRef}
      controls
      className="w-full max-w-xs"
      style={{ height: 32 }}
    />
  );
}
