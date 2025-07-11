// file: hooks/useSpeech.tsx (Final, Bulletproof Version)

import { useState, useEffect, useRef, useCallback } from 'react';

// Explicit interface for SpeechRecognition
interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => any) | null;
  onend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onerror: ((this: SpeechRecognition, ev: SpeechRecognitionErrorEvent) => any) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

interface SpeechRecognitionConstructor {
  new (): SpeechRecognition;
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message: string;
}

type SpeechState = 'idle' | 'speaking' | 'listening';

interface SpeechHook {
  speechState: SpeechState;
  transcript: string;
  speak: (text: string, options?: { onEnd?: () => void }) => void;
  startListening: () => void;
  stopListening: () => void;
  cancelAll: () => void;
  hasRecognitionSupport: boolean;
}

const SpeechRecognitionAPI: SpeechRecognitionConstructor | null =
  (typeof window !== 'undefined' && ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition)) || null;

export const useSpeech = (): SpeechHook => {
  const [speechState, setSpeechState] = useState<SpeechState>('idle');
  const [transcript, setTranscript] = useState('');
  
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  // --- NEW: A ref to hold the Audio object ---
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const cancelAll = useCallback(() => {
    // Stop any browser TTS that might be running
    if (typeof window !== 'undefined') window.speechSynthesis.cancel();
    
    // Stop any audio element that might be playing
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = ''; // Detach the audio source
      audioRef.current = null;
    }

    // Stop any listening
    if (recognitionRef.current) recognitionRef.current.abort();
    
    setSpeechState('idle');
  }, []);

  // --- THIS IS THE UPDATED 'speak' FUNCTION ---
  const speak = useCallback((text: string, options?: { onEnd?: () => void }) => {
    if (!text) return;
    
    cancelAll(); // Stop anything currently happening

    setSpeechState('speaking');

    // Create a new Audio object
    const newAudio = new Audio();
    audioRef.current = newAudio;

    // Construct the URL for our new backend TTS endpoint
    const url = `${process.env.NEXT_PUBLIC_API_URL}/speak?text=${encodeURIComponent(text)}`;
    newAudio.src = url;

    // When the audio has finished playing, clean up and call the onEnd callback
    newAudio.onended = () => {
      setSpeechState('idle');
      if (options && options.onEnd) options.onEnd();
    };

    newAudio.onerror = (e) => {
      console.error("Audio playback error:", e);
      setSpeechState('idle');
      if (options && options.onEnd) options.onEnd();
    };

    // Start playing the audio stream from our backend
    newAudio.play();

  }, [cancelAll]);
  // --- END OF UPDATED 'speak' FUNCTION ---

  const startListening = useCallback(() => {
    if (speechState !== 'idle' || !recognitionRef.current) return;
    cancelAll();
    setSpeechState('listening');
    setTranscript('');
    try {
      recognitionRef.current.start();
    } catch (e) {
      // Catch the "already started" error, just in case.
      console.error("Could not start listening:", e);
      setSpeechState('idle');
    }
  }, [speechState, cancelAll]);
  
  const stopListening = useCallback(() => {
    if (!recognitionRef.current) return;
    recognitionRef.current.stop();
    setSpeechState('idle');
  }, [speechState]);

  useEffect(() => {
    if (!SpeechRecognitionAPI) {
      return;
    }
    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      const result = event.results[event.results.length - 1][0].transcript.trim();
      setTranscript(result);
      setSpeechState('idle');
    };

    recognition.onend = () => {
      setSpeechState('idle');
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (event.error !== 'no-speech' && event.error !== 'aborted') {
        console.error('Speech recognition error:', event.error);
      }
      setSpeechState('idle');
    };

    recognitionRef.current = recognition;

    return () => {
      cancelAll();
    };
  }, [cancelAll]);

  return {
    speechState,
    transcript,
    speak,
    startListening,
    stopListening,
    cancelAll,
    hasRecognitionSupport: !!SpeechRecognitionAPI,
  };
};