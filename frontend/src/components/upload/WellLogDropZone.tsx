import React, { useRef } from 'react';
import { Upload } from 'lucide-react';

interface WellLogDropZoneProps {
  onFile: (file: File) => void;
}

export const WellLogDropZone: React.FC<WellLogDropZoneProps> = ({ onFile }) => {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files?.[0]) onFile(e.dataTransfer.files[0]);
  };

  return (
    <div
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className="relative border-2 border-dashed border-[#efb027] bg-[#241a0a]/80 hover:bg-[#2e2308] transition-all p-5 text-center cursor-pointer rounded group cyber-glow-amber"
    >
      <div className="absolute top-1 left-1 text-[0.6rem] text-[#efb027] font-bold">[+]</div>
      <div className="absolute top-1 right-1 text-[0.6rem] text-[#efb027] font-bold">[+]</div>
      <div className="absolute bottom-1 left-1 text-[0.6rem] text-[#efb027] font-bold">[+]</div>
      <div className="absolute bottom-1 right-1 text-[0.6rem] text-[#efb027] font-bold">[+]</div>

      <input
        ref={inputRef}
        type="file"
        accept=".las,.csv,.txt"
        onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
        className="hidden"
      />
      <Upload className="w-8 h-8 mx-auto text-[#efb027] group-hover:scale-110 transition-transform duration-200" />
      <p className="text-[#efb027] text-sm font-bold mt-2 mb-0.5 tracking-wider uppercase">
        DROP .LAS OR .CSV
      </p>
      <p className="text-[#6b5a2e] text-xs uppercase tracking-wide font-semibold">
        LAS AUTO-CONVERTS TO TENSOR
      </p>
    </div>
  );
};
