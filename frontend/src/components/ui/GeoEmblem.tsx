import React from 'react';
import xgboostIcon from '../../assets/xgboost.svg';

// The XGBoost mark, under the curve list. Decorative; sized to its content so
// the curve table keeps the spare height.
export const GeoEmblem: React.FC = () => (
  <div className="shrink-0 flex items-center justify-center py-2">
    <div className="relative">
      <div className="absolute inset-0 rounded-full bg-[#efb027] opacity-10 blur-xl" />
      <img
        src={xgboostIcon}
        alt=""
        aria-hidden="true"
        className="relative w-28 h-28 object-contain opacity-80 drop-shadow-[0_0_10px_rgba(239,176,39,0.4)]"
      />
    </div>
  </div>
);
