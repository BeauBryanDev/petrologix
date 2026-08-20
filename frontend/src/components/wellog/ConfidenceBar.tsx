import React from 'react';
import { LithologyShare } from '../../types/prediction';

interface ConfidenceBarProps {
  shares: LithologyShare[];
}

export const ConfidenceBar: React.FC<ConfidenceBarProps> = ({ shares }) => {
  const top = shares[0];
  const confidence = top?.mean_confidence ?? 0;

  return (
    <div className="border-2 border-[#4a3813] bg-[#241a0a] rounded p-3 mb-3">
      <div className="flex items-center justify-between mb-1.5">
        <p className="text-[#6b5a2e] text-xs m-0 font-mono font-bold uppercase tracking-wider">
          INFERENCE CONFIDENCE
        </p>
        <span className="text-[#efb027] text-sm font-mono font-bold">
          {(confidence * 100).toFixed(0)}% ({confidence.toFixed(2)})
        </span>
      </div>

      <div className="bg-[#2e2308] border border-[#4a3813] rounded h-3 my-1.5 overflow-hidden p-0.5">
        <div
          className="bg-[#efb027] h-full rounded transition-all duration-500 shadow-[0_0_10px_#efb027]"
          style={{ width: `${Math.round(confidence * 100)}%` }}
        />
      </div>

      <div className="grid grid-cols-2 gap-x-2 gap-y-1 mt-2 pt-2 border-t border-[#4a3813] text-[0.68rem] font-mono text-[#a3893f]">
        {shares.slice(0, 4).map((s) => (
          <div key={s.lithology} className="flex justify-between">
            <span className="uppercase truncate pr-1">{s.lithology}:</span>
            <span className="text-[#e8ddc7] font-bold">{(s.fraction * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
};
