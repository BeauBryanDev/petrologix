import React from 'react';
import geologyIcon from '../../assets/geology_icon.svg';

// Decorative only. Fills the gap between the curve list and the sample picker.
export const GeoEmblem: React.FC = () => (
  <div className="flex-1 flex items-center justify-center min-h-[80px] py-2">
    <div className="relative">
      <div className="absolute inset-0 rounded-full bg-[#efb027] opacity-10 blur-xl" />
      <img
        src={geologyIcon}
        alt=""
        aria-hidden="true"
        className="relative w-20 h-20 object-contain opacity-80 drop-shadow-[0_0_10px_rgba(239,176,39,0.4)]"
      />
    </div>
  </div>
);
