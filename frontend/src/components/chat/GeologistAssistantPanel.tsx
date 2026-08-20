import React from 'react';
import { Sparkles } from 'lucide-react';
import { useSessionStore } from '../../stores/sessionStore';
import { CornerReticles } from '../ui/CornerReticles';
import { PanelHeader } from '../ui/PanelHeader';
import { ChatInput } from './ChatInput';
import { ChatPanel } from './ChatPanel';
import { QuickActions } from './QuickActions';

export const GeologistAssistantPanel: React.FC = () => {
  const { messages, sendMessage, llmStatus, prediction } = useSessionStore();
  const busy = llmStatus === 'busy';

  return (
    <div className="relative bg-[#1c1409] p-4 flex flex-col h-full select-none">
      <CornerReticles />

      <PanelHeader
        section="SEC-02"
        title="GEOLOGIST AI CORE"
        className="mb-3"
        right={
          <div className="flex items-center gap-2 text-xs text-[#a3893f]">
            <Sparkles className="w-4 h-4 text-[#efb027] animate-pulse" />
            <span>
              MODEL: <span className="text-[#efb027] font-bold">{prediction?.model_version ?? '--'}</span>
            </span>
          </div>
        }
      />

      <ChatPanel messages={messages} busy={busy} />

      <QuickActions
        onSelect={sendMessage}
        disabled={busy}
        depthRange={prediction?.depth_range}
      />

      <ChatInput onSend={sendMessage} disabled={busy} />
    </div>
  );
};
