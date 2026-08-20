import React from 'react';
import { SampleWell } from '../../types/wellLog';

interface SampleWellPickerProps {
  samples: SampleWell[];
  activeId: string | null;
  onSelect: (id: string) => void;
  disabled?: boolean;
}

export const SampleWellPicker: React.FC<SampleWellPickerProps> = ({
  samples,
  activeId,
  onSelect,
  disabled,
}) => (
  <div className="mt-auto pt-3 border-t border-[#4a3813]">
    <p className="text-[#6b5a2e] text-xs font-mono font-bold uppercase tracking-wider mb-2">
      SELECT SAMPLE RESERVOIR
    </p>
    <div className="flex flex-col gap-2">
      {samples.map((sample) => (
        <button
          key={sample.id}
          disabled={disabled}
          onClick={() => onSelect(sample.id)}
          className={`text-left text-xs px-3 py-2 rounded border transition-all flex items-center justify-between font-mono disabled:opacity-60 ${
            activeId === sample.id
              ? 'bg-[#2e2308] border-[#efb027] text-[#efb027] font-bold cyber-glow-amber'
              : 'bg-[#241a0a] border-[#4a3813] text-[#a3893f] hover:border-[#a3893f]'
          }`}
        >
          <div>
            <div className="font-semibold text-xs">{sample.label}</div>
            <div className="text-[0.68rem] text-[#6b5a2e]">
              {sample.description} ({sample.depth_range[1].toFixed(0)}m)
            </div>
          </div>
          <span className="text-[0.68rem] bg-[#1c1409] px-2 py-0.5 rounded border border-[#4a3813] font-bold">
            SELECT
          </span>
        </button>
      ))}
    </div>
  </div>
);
