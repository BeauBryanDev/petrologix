import React from 'react';
import { FileSpreadsheet, Layers } from 'lucide-react';

type Format = 'LAS' | 'CSV';

interface FormatToggleProps {
  value: Format;
  onChange: (format: Format) => void;
}

const buttonClass = (active: boolean) =>
  `py-2 text-xs rounded transition-all text-center border font-mono font-bold uppercase tracking-wider flex items-center justify-center gap-1.5 ${
    active
      ? 'bg-[#2e2308] border-[#efb027] text-[#efb027] cyber-glow-amber'
      : 'bg-[#241a0a] border-[#4a3813] text-[#6b5a2e] hover:border-[#a3893f]'
  }`;

export const FormatToggle: React.FC<FormatToggleProps> = ({ value, onChange }) => (
  <div className="grid grid-cols-2 gap-2">
    <button onClick={() => onChange('LAS')} className={buttonClass(value === 'LAS')}>
      <Layers className="w-4 h-4" />
      <span>LAS FORMAT</span>
    </button>
    <button onClick={() => onChange('CSV')} className={buttonClass(value === 'CSV')}>
      <FileSpreadsheet className="w-4 h-4" />
      <span>CSV FORMAT</span>
    </button>
  </div>
);
