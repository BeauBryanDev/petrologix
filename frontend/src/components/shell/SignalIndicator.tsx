import React, { useEffect, useState } from 'react';
import { Radio } from 'lucide-react';
import { getHealth } from '../../services/api';
import { useSessionStore } from '../../stores/sessionStore';

const POLL_MS = 15000;

export const SignalIndicator: React.FC = () => {
  const { llmStatus, xgboostStatus } = useSessionStore();
  const [reachable, setReachable] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;

    const ping = async () => {
      const ok = await getHealth();
      if (!cancelled) setReachable(ok);
    };

    ping();
    const interval = setInterval(ping, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const degraded = llmStatus === 'offline' || xgboostStatus === 'error';

  const { label, colour, pulse } =
    reachable === null
      ? { label: 'LINKING', colour: '#6b5a2e', pulse: true }
      : !reachable
        ? { label: 'LOST', colour: '#d9614a', pulse: false }
        : degraded
          ? { label: 'DEGRADED', colour: '#c99a3a', pulse: true }
          : { label: 'STABLE', colour: '#efb027', pulse: true };

  return (
    <div
      className="flex items-center gap-2"
      title={
        reachable === false
          ? 'The Petrologix backend is not responding.'
          : degraded
            ? `LLM ${llmStatus} / XGBoost ${xgboostStatus}`
            : 'Backend reachable, engines nominal.'
      }
    >
      <Radio
        className={`w-5 h-5 ${pulse ? 'animate-pulse' : ''}`}
        style={{ color: colour }}
      />
      <span className="font-semibold" style={{ color: colour }}>
        SIGNAL: {label}
      </span>
    </div>
  );
};
