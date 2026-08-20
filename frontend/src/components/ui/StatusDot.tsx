import React from 'react';

interface StatusDotProps {
  active?: boolean;
}

export const StatusDot: React.FC<StatusDotProps> = ({ active = true }) => (
  <div
    className={`w-2.5 h-2.5 rounded-full ${
      active ? 'bg-[#efb027] shadow-[0_0_8px_#efb027] animate-pulse' : 'bg-[#6b5a2e]'
    }`}
  />
);
