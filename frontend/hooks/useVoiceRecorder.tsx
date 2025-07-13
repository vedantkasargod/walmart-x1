// file: hooks/useVoiceRecorder.tsx (Final version using the 'web-vad' library)

import { useState, useRef, useCallback, useEffect } from 'react';
import { VAD } from 'web-vad';

// This special import syntax is required by Next.js/Webpack to handle the worklet file.
// @ts-ignore
import AudioWorkletURL from 'web-vad/dist/worklet.js?worker&url';

// Helper function to convert the VAD's audio chunks to a WAV Blob
function audioChunksToWavBlob(chunks: Float32Array[], sampleRate: number): Blob {
  const pcm = new Float32Array(chunks.reduce((acc, val) => acc + val.length, 0));
  let offset = 0;
  for (const chunk of chunks) {
    pcm.set(chunk, offset);
    offset += chunk.length;
  }
  
  const dataView = new DataView(new ArrayBuffer(44 + pcm.length * 2));
  const writeString = (view: DataView, offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };
  
  writeString(dataView, 0, 'RIFF');
  dataView.setUint32(4, 36 + pcm.length * 2, true);
  writeString(dataView, 8, 'WAVE');
  writeString(dataView, 12, 'fmt ');
  dataView.setUint32(16, 16, true);
  dataView.setUint16(20, 1, true);
  dataView.setUint16(22, 1, true);
  dataView.setUint32(24, sampleRate, true);
  dataView.setUint32(28, sampleRate * 4, true);
  dataView.setUint16(32, 2, true);
  dataView.setUint16(34, 16, true);
  writeString(dataView, 36, 'data');
  dataView.setUint32(40, pcm.length * 2, true);

  for (let i = 0; i < pcm.length; i++) {
    dataView.setInt16(44 + i * 2, pcm[i] * 0x7FFF, true);
  }

  return new Blob([dataView], { type: 'audio/wav' });
}


type AgentState = 'idle' | 'loading' | 'recording' | 'speaking';

export function useVoiceRecorder() {
  const [agentState, setAgentState] = useState<AgentState>('idle');
  const [transcript, setTranscript] = useState('');
  
  const vadRef = useRef<VAD | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioChunksRef = useRef<Float32Array[]>([]);

  const onSpeechEnd = useCallback(async () => {
    if (audioChunksRef.current.length === 0) {
      console.log("Speech ended with no audio chunks, ignoring.");
      return;
    }

    console.log("Speech ended. Processing audio...");
    const wavBlob = audioChunksToWavBlob(audioChunksRef.current, 16000); // VAD works at 16kHz
    audioChunksRef.current = []; // Reset chunks
    
    const formData = new FormData();
    formData.append('audio', wavBlob, 'user_audio.wav');

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/transcribe_audio`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) throw new Error('Transcription failed');
      const data = await response.json();
      if (data.transcript) {
        setTranscript(data.transcript);
      }
    } catch (err) {
      console.error('Transcription error:', err);
    }
  }, []);

  const initializeVAD = useCallback(async () => {
    try {
      setAgentState('loading');
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      const vad = new VAD({
        workletURL: AudioWorkletURL,
        modelUrl: '/silero_vad.onnx', // Points to the file in your /public directory
        stream: stream,
        onSpeechEnd: onSpeechEnd,
        onSpeechStart: () => {
          console.log("User started speaking.");
          setAgentState('recording');
        },
      });
      
      await vad.init();
      vadRef.current = vad;
      setAgentState('idle');
    } catch (error) {
      console.error("VAD initialization failed:", error);
      setAgentState('idle');
    }
  }, [onSpeechEnd]);

  useEffect(() => {
    initializeVAD();
    return () => {
      vadRef.current?.destroy();
    };
  }, [initializeVAD]);

  const startRecording = () => vadRef.current?.start();
  const stopRecording = () => vadRef.current?.destroy();

  const speak = useCallback((text: string, onEnd?: () => void) => {
    // ... your speak function remains the same, it should pause/resume the VAD
    vadRef.current?.pause();
    // ...
    // onended: () => { vadRef.current?.start(); ... }
  }, []);

  return { agentState, transcript, startRecording, stopRecording, speak };
}