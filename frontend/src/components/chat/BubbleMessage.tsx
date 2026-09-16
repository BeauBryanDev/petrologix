import React from 'react';
import { Terminal } from 'lucide-react';
import { ChatMessage } from '../../types/chat';
import { GeoAvatar } from './GeoAvatar';
import { MarkdownText } from './MarkdownText';
import { CopyButton } from './CopyButton';

interface BubbleMessageProps {
  message: ChatMessage;
}

export const BubbleMessage: React.FC<BubbleMessageProps> = ({ message }) => {
  const isUser = message.sender === 'user';

  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
      {isUser ? (
        <div className="bg-[#2e2308] border border-[#4a3813] rounded-md px-4 py-3 max-w-[85%] shadow-md">
          <div className="flex items-center gap-2 mb-1.5 border-b border-[#4a3813] pb-1">
            <Terminal className="w-3.5 h-3.5 text-[#a3893f]" />
            <span className="text-[0.68rem] text-[#a3893f] font-mono uppercase font-bold">
              GEOLOGIST_USER_QUERY
            </span>
            <span className="text-[0.68rem] text-[#6b5a2e] ml-auto font-semibold">{message.timestamp}</span>
          </div>
          <p className="text-[#e8ddc7] text-base font-mono m-0 leading-relaxed select-text cursor-text">
            {message.text}
          </p>
        </div>
      ) : (
        <div className="bg-[#241a0a] border-2 border-[#efb027] rounded-md px-4 py-3.5 max-w-[92%] cyber-glow-amber">
          <div className="flex items-center justify-between gap-2 mb-2 border-b border-[#4a3813] pb-1.5">
            <div className="flex items-center gap-2">
              <GeoAvatar />
              <span className="text-[#efb027] text-sm font-bold tracking-widest font-mono uppercase">
                {message.authorName || 'PETROLOGIX'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {message.faciesContext && (
                <span className="text-[0.6rem] bg-[#2e2308] border border-[#efb027] text-[#efb027] px-2 py-0.5 rounded font-bold uppercase">
                  FACIES: {message.faciesContext}
                </span>
              )}
              <span className="text-[0.68rem] text-[#6b5a2e] font-semibold">{message.timestamp}</span>
              <CopyButton text={message.text} />
            </div>
          </div>
          {/* Claude answers in markdown, so **text** has to render as bold
              rather than reach the user as asterisks. MarkdownText keeps the
              pre-wrap the MEASURED block needs for its column alignment. */}
          {message.streaming && !message.text ? (
            <span className="text-[#efb027] text-xs font-mono font-bold tracking-wider animate-pulse">
              {message.status ?? 'PROCESSING SUBSURFACE TENSOR INFERENCE...'}
            </span>
          ) : (
            <MarkdownText text={message.text} />
          )}
        </div>
      )}
    </div>
  );
};
