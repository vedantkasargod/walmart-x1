// file: hooks/useSpeech.tsx (Final, Bulletproof Version)

import { useState, useEffect, useRef, useCallback } from "react";

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

const SpeechRecognitionAPI: SpeechRecognitionConstructor | null =
  typeof window !== "undefined" && ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition) || null;

export const useSpeech = () => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [hasRecognitionSupport, setHasRecognitionSupport] = useState(!!SpeechRecognitionAPI);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const cancelAll = useCallback(() => {
    if (typeof window !== "undefined") window.speechSynthesis.cancel();
    if (recognitionRef.current) recognitionRef.current.abort();
    setIsListening(false);
    setIsSpeaking(false);
  }, []);

  // Updated speak function to accept options object with onEnd
  const speak = useCallback((text: string, { onEnd }: { onEnd?: () => void } = {}) => {
    if (!window.speechSynthesis || !text) {
      if (onEnd) onEnd();
      return;
    }
    cancelAll();
    const utterance = new window.SpeechSynthesisUtterance(text);
    setIsSpeaking(true);
    utterance.onend = () => {
      setIsSpeaking(false);
      if (onEnd) onEnd();
    };
    utterance.onerror = (event) => {
      // @ts-ignore
      console.error("Speech synthesis error:", event.error);
      setIsSpeaking(false);
      if (onEnd) onEnd();
    };
    window.speechSynthesis.speak(utterance);
  }, [cancelAll]);

  const startListening = useCallback(() => {
    if (!recognitionRef.current || isSpeaking) return;
    cancelAll();
    setTranscript("");
    setIsListening(true);
    recognitionRef.current.start();
  }, [isSpeaking, cancelAll]);

  const stopListening = useCallback(() => {
    if (!recognitionRef.current) return;
    recognitionRef.current.stop();
    setIsListening(false);
  }, []);

  useEffect(() => {
    if (!SpeechRecognitionAPI) {
      setHasRecognitionSupport(false);
      return;
    }
    setHasRecognitionSupport(true);
    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
      const result = event.results[event.results.length - 1][0].transcript.trim();
      setTranscript(result);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (event.error !== "no-speech" && event.error !== "aborted") {
        console.error("Speech recognition error:", event.error);
      }
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      cancelAll();
    };
  }, [cancelAll]);

  return {
    isListening,
    transcript,
    hasRecognitionSupport,
    isSpeaking,
    startListening,
    stopListening,
    speak,
    cancelAll,
  };
};