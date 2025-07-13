"use client";
import { useEffect } from 'react';
import { useVoiceRecorder } from '@/hooks/useVoiceRecorder';
import { Button } from '@/components/ui/button';
import { Mic, Square } from 'lucide-react';

interface VoiceControllerProps {
    handleVoiceCommand: (transcript: string) => void;
}
// This component now holds all the voice logic
export default function VoiceController({ handleVoiceCommand }: VoiceControllerProps) {
    const { agentState, transcript, startRecording, stopRecording } = useVoiceRecorder();

    // This effect listens for the final transcript and passes it up to the main page
    useEffect(() => {
        if (transcript) {
            handleVoiceCommand(transcript);
        }
    }, [transcript, handleVoiceCommand]);

    return (
        <Button
            size="icon"
            variant="outline"
            onClick={agentState === 'recording' ? stopRecording : startRecording}
            className={`ml-2 rounded-full w-12 h-12 ${agentState === 'recording' ? 'bg-red-500 text-white animate-pulse' : ''}`}
        >
            {agentState === 'recording' ? (
                <Square className="w-6 h-6" />
            ) : (
                <Mic className="w-6 h-6" />
            )}
        </Button>
    );
}