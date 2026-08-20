import React from 'react';
import geologyIcon from '../../assets/geology_icon.svg';

// Decorative only. Fills the gap between the curve list and the sample picker.
export const GeoEmblem: React.FC = () => (
  <div className="flex-1 flex items-center justify-center min-h-[120px] py-2">
    <div className="relative">
      <div className="absolute inset-0 rounded-full bg-[#efb027] opacity-10 blur-2xl" />
      <img
        src={geologyIcon}
        alt=""
        aria-hidden="true"
        className="relative w-36 h-36 object-contain opacity-80 animate-cyber-pulse drop-shadow-[0_0_12px_rgba(239,176,39,0.45)]"
      />
    </div>
  </div>
);
