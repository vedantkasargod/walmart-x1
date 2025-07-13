// file: hooks/useSpeech.tsx (Final HTTP Auto-Stop Voice Agent)

import { useState, useRef, useCallback, useEffect } from 'react';

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

export const useSpeech = (): SpeechHook => {
  const [speechState, setSpeechState] = useState<SpeechState>('idle');
  const [transcript, setTranscript] = useState('');

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // Check for MediaRecorder support
  const [hasRecognitionSupport] = useState(
    typeof window !== 'undefined' &&
    !!navigator.mediaDevices &&
    !!window.MediaRecorder
  );

  const stopAll = useCallback(() => {
    // Stop any speaking
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
    // Stop any listening
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
    }
    // Release the microphone
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach(track => track.stop());
      audioStreamRef.current = null;
    }
    // Clear silence timer
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    setSpeechState('idle');
  }, []);

  const speak = useCallback((text: string, options?: { onEnd?: () => void }) => {
    if (!text) return;
    stopAll();
    setSpeechState('speaking');
    const newAudio = new Audio();
    newAudio.src = `${process.env.NEXT_PUBLIC_API_URL}/speak?text=${encodeURIComponent(text)}`;
    newAudio.onended = () => {
      setSpeechState('idle');
      if (options && options.onEnd) options.onEnd();
    };
    newAudio.onerror = () => {
      console.error("Audio playback error.");
      setSpeechState('idle');
      if (options && options.onEnd) options.onEnd();
    };
    newAudio.play();
    audioRef.current = newAudio;
  }, [stopAll]);

  // --- Final HTTP Auto-Stop Voice Agent ---
  const startListening = useCallback(async () => {
    if (speechState !== 'idle') return;
    stopAll();
    setTranscript('');
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000
        }
      });
      audioStreamRef.current = stream;

      const recorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
        audioBitsPerSecond: 16000
      });
      mediaRecorderRef.current = recorder;

      // Silence auto-stop logic
      const resetSilenceTimer = () => {
        if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = setTimeout(() => {
          stopListening();
        }, 1500); // 1.5 seconds of silence
      };

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
          resetSilenceTimer();
        }
      };

      recorder.onstop = async () => {
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }
        if (audioStreamRef.current) {
          audioStreamRef.current.getTracks().forEach(track => track.stop());
          audioStreamRef.current = null;
        }
        setSpeechState('idle');
        // Combine chunks and send to backend
        const audioBlob = new Blob(chunksRef.current, { type: recorder.mimeType });
        const formData = new FormData();
        formData.append('audio', audioBlob, 'user_audio.webm');
        try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
          const response = await fetch(`${apiUrl}/transcribe_audio`, {
            method: 'POST',
            body: formData
          });
          if (!response.ok) throw new Error('Transcription failed');
          const data = await response.json();
          if (data.transcript) setTranscript(data.transcript);
        } catch (err) {
          console.error('Transcription error:', err);
        }
      };

      recorder.start(250); // 250ms chunks
      setSpeechState('listening');
      resetSilenceTimer();
    } catch (error) {
      console.error('Failed to start listening:', error);
      setSpeechState('idle');
    }
  }, [speechState, stopAll]);

  const stopListening = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }, []);

  const cancelAll = useCallback(() => {
    stopAll();
  }, [stopAll]);

  useEffect(() => {
    return () => stopAll();
  }, [stopAll]);

  return {
    speechState,
    transcript,
    speak,
    startListening,
    stopListening,
    cancelAll,
    hasRecognitionSupport,
  };
};