import React, { useState } from 'react';
import { CornerDownLeft } from 'lucide-react';

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled }) => {
  const [text, setText] = useState('');

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text);
    setText('');
  };

  return (
    <form onSubmit={submit} className="flex gap-2">
      <div className="relative flex-1">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#efb027] font-bold text-sm font-mono">{'>'}</span>
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="ask about this well log formation..."
          className="w-full bg-[#241a0a] border border-[#4a3813] focus:border-[#efb027] text-[#e8ddc7] placeholder-[#6b5a2e] text-sm sm:text-base pl-8 pr-3 py-2.5 rounded font-mono focus:outline-none transition-all cyber-glow-amber"
        />
      </div>
      <button
        type="submit"
        disabled={!text.trim() || disabled}
        className="bg-[#efb027] hover:bg-[#ffc107] disabled:opacity-50 text-[#1c1409] font-bold text-xs sm:text-sm px-5 py-2.5 rounded transition-all font-mono flex items-center gap-1.5 cursor-pointer uppercase tracking-wider cyber-glow-amber shrink-0"
      >
        <span>SEND</span>
        <CornerDownLeft className="w-4 h-4" />
      </button>
    </form>
  );
};
