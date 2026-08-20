import React from 'react';
import { Terminal, HardDrive, Cpu, Radio } from 'lucide-react';

export const FooterBar: React.FC = () => {
  return (
    <footer className="relative px-4 py-1.5 bg-[#1c1409] border-t-2 border-[#4a3813] flex items-center justify-between text-xs text-[#6b5a2e] font-mono h-9 select-none">
      {/* Bottom Corner Tech Accents */}
      <div className="absolute bottom-0 left-0 w-3.5 h-3.5 border-b-2 border-l-2 border-[#efb027]" />
      <div className="absolute bottom-0 right-0 w-3.5 h-3.5 border-b-2 border-r-2 border-[#efb027]" />

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5 text-[#a3893f]">
          <Terminal className="w-4 h-4 text-[#efb027]" />
          <span>MODEL:</span>
          <span className="text-[#efb027] font-semibold">qwen2.5-7b-4bit · t4</span>
        </div>

        <span className="text-[#4a3813]">|</span>

        <div className="hidden sm:flex items-center gap-1.5">
          <Cpu className="w-4 h-4 text-[#6b5a2e]" />
          <span>GPU UTILS:</span>
          <span className="text-[#e8ddc7] font-semibold">42% [T4 16GB]</span>
        </div>

        <span className="hidden sm:inline text-[#4a3813]">|</span>

        <div className="hidden md:flex items-center gap-1.5">
          <HardDrive className="w-4 h-4 text-[#6b5a2e]" />
          <span>SAMPLING:</span>
          <span className="text-[#e8ddc7] font-semibold">1.0m STEP</span>
        </div>
      </div>

      <div className="flex items-center gap-3 text-xs">
        <div className="flex items-center gap-1.5">
          <Radio className="w-3.5 h-3.5 text-[#efb027] animate-pulse" />
          <span className="text-[#a3893f] font-semibold">SIGNAL: STABLE</span>
        </div>
        <span className="text-[#4a3813]">|</span>
        <span className="text-[#efb027] bg-[#2e2308] px-2.5 py-0.5 border border-[#efb027]/40 rounded text-[0.68rem] font-bold uppercase tracking-wider">
          RESEARCH PREVIEW
        </span>
      </div>
    </footer>
  );
};
