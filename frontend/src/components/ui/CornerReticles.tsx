import React from 'react';

// Corner brackets repeated on every HUD panel.
export const CornerReticles: React.FC = () => (
  <>
    <div className="absolute top-2 left-2 w-2.5 h-2.5 border-t-2 border-l-2 border-[#efb027]" />
    <div className="absolute top-2 right-2 w-2.5 h-2.5 border-t-2 border-r-2 border-[#efb027]" />
    <div className="absolute bottom-2 left-2 w-2.5 h-2.5 border-b-2 border-l-2 border-[#efb027]" />
    <div className="absolute bottom-2 right-2 w-2.5 h-2.5 border-b-2 border-r-2 border-[#efb027]" />
  </>
);
