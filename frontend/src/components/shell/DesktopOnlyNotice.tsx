import React from 'react';
import { Monitor } from 'lucide-react';
import geoMindIcon from '../../assets/geo_mind.svg';

// Shown instead of the console below 1280px. The three panels are meant to be
// read together, so a narrow viewport gets an honest notice rather than a
// stacked layout that looks broken.
export const DesktopOnlyNotice: React.FC = () => (
<div className="xl:hidden flex-1 flex items-center justify-center p-6 relative z-10">
    <div className="max-w-md w-full bg-[#241a0a] border-2 border-[#4a3813] rounded p-6 text-center cyber-glow-amber">
      <div className="flex items-center justify-center gap-3 mb-4">
        <div className="w-10 h-10 rounded bg-[#2e2308] border border-[#efb027] flex items-center justify-center">
          <img src={geoMindIcon} alt="" aria-hidden="true" className="w-7 h-7 object-contain" />
        </div>
        <span className="text-[#efb027] text-xl font-bold tracking-widest uppercase font-mono cyber-glow-text">
          PETROLOGIX
          
        </span>
      </div>

      <Monitor className="w-10 h-10 text-[#efb027] mx-auto mb-3" />

      <h2 className="text-[#efb027] text-base font-bold tracking-widest uppercase font-mono mb-3">
        Desktop display required
      </h2>
      {/* This is no a mobile first friendly design, but it's a console, so it's fine. */}
      <p className="text-[#e8ddc7] text-sm font-mono leading-relaxed mb-4">
        This console reads a well log, the facies prediction and the geologist
        assistant side by side. It needs a viewport of at least 1280px.
      </p>

      <p className="text-[#6b5a2e] text-xs font-mono uppercase tracking-wider">
        Open it on a laptop or desktop
      </p>
    </div>
  </div>
);
