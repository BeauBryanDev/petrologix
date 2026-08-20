import React from 'react';
import { LithologyShare } from '../../types/prediction';

interface FaciesResultProps {
  top?: LithologyShare;
}

export const FaciesResult: React.FC<FaciesResultProps> = ({ top }) => (
  <div className="border-2 border-[#4a3813] bg-[#241a0a] rounded p-3 mb-3 cyber-glow-amber">
    <div className="flex items-center justify-between mb-1">
      <p className="text-[#6b5a2e] text-xs m-0 font-mono font-bold uppercase tracking-wider">
        PREDICTED LITHO-FACIES
      </p>
      <span className="text-[0.68rem] bg-[#2e2308] border border-[#efb027] text-[#efb027] px-2 py-0.5 rounded font-bold uppercase">
        XGBOOST
      </span>
    </div>
    <p className="text-[#efb027] text-2xl font-bold m-0 tracking-widest font-mono uppercase cyber-glow-text">
      {top?.lithology ?? '---'}
    </p>
  </div>
);
