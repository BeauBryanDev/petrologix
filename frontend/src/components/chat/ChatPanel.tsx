import React, { useEffect, useRef } from 'react';
import { ChatMessage } from '../../types/chat';
import { BubbleMessage } from './BubbleMessage';
import { GeoAvatar } from './GeoAvatar';

interface ChatPanelProps {
  messages: ChatMessage[];
  busy: boolean;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ messages, busy }) => {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, busy]);

  return (
    <div className="flex-1 overflow-y-auto space-y-3.5 pr-2 mb-3 max-h-[calc(100vh-280px)] min-h-[300px]">
      {messages.map((msg) => (
        <BubbleMessage key={msg.id} message={msg} />
      ))}

      {busy && (
        <div className="items-start">
          <div className="bg-[#241a0a] border border-[#efb027] rounded-md px-4 py-3 max-w-[80%] flex items-center gap-3 cyber-glow-amber">
            <GeoAvatar spinning />
            <span className="text-[#efb027] text-xs font-mono font-bold tracking-wider animate-pulse">
              PROCESSING SUBSURFACE TENSOR INFERENCE...
            </span>
          </div>
        </div>
      )}

      <div ref={endRef} />
    </div>
  );
};
