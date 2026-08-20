import React from 'react';
import { BarChart3, Microscope, Zap } from 'lucide-react';

interface QuickActionsProps {
  onSelect: (prompt: string) => void;
  disabled?: boolean;
  depthRange?: [number, number];
}

const chipClass =
  'text-xs bg-[#2e2308] border border-[#4a3813] hover:border-[#efb027] text-[#a3893f] ' +
  'hover:text-[#efb027] px-3 py-1.5 rounded transition-all font-mono font-semibold ' +
  'flex items-center gap-1.5 disabled:opacity-50';

export const QuickActions: React.FC<QuickActionsProps> = ({ onSelect, disabled, depthRange }) => {
  const [start, end] = depthRange ?? [0, 0];

  return (
    <div className="flex flex-wrap gap-2 mb-3 pt-2 border-t border-[#4a3813]">
      <button
        disabled={disabled}
        onClick={() => onSelect(`interpret facies for interval ${start.toFixed(0)}-${end.toFixed(0)}m`)}
        className={chipClass}
      >
        <Zap className="w-3.5 h-3.5" />
        Interpret facies interval
      </button>
      <button disabled={disabled} onClick={() => onSelect('calculate Vshale from GR')} className={chipClass}>
        <BarChart3 className="w-3.5 h-3.5" />
        Vshale calculation
      </button>
      <button
        disabled={disabled}
        onClick={() => onSelect('check porosity and density crossover')}
        className={chipClass}
      >
        <Microscope className="w-3.5 h-3.5" />
        Density porosity crossover
      </button>
    </div>
  );
};
