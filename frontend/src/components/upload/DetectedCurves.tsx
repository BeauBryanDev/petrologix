import React from 'react';
import { AlertTriangle, Check } from 'lucide-react';
import { CurveReport } from '../../types/wellLog';

interface DetectedCurvesProps {
  report?: CurveReport;
}
// Well  Log - Electric Curves 
const CURVE_LABELS: Record<string, string> = {
  GR: 'GAMMA RAY (API)',
  RDEP: 'RESISTIVITY DEEP (OHM.M)',
  RMED: 'RESISTIVITY MED (OHM.M)',
  RHOB: 'BULK DENSITY (G/CC)',
  NPHI: 'NEUTRON POROSITY',
  DTC: 'SONIC (US/FT)',
  CALI: 'CALIPER (IN)',
  DRHO: 'DENSITY CORRECTION',
  PEF: 'PHOTOELECTRIC (B/E)',
  RSHA: 'RESISTIVITY SHALLOW',
  RXO: 'FLUSHED ZONE RESIST.',
  SP: 'SPONTANEOUS POT. (MV)',
  ROP: 'RATE OF PENETRATION',
};

export const DetectedCurves: React.FC<DetectedCurvesProps> = ({ report }) => {
  const present = report?.required_present ?? [];
  const missing = report?.required_missing ?? [];
  const optional = report?.optional_present ?? [];
  const total = present.length + optional.length;

  return (
    <div className="bg-[#241a0a] border border-[#4a3813] p-3 rounded h-full min-h-0 flex flex-col">
      <div className="flex items-center justify-between mb-2 shrink-0">
        <p className="text-[#a3893f] text-sm font-mono font-bold uppercase tracking-wider">
          CURVES DETECTED
        </p>
        <span className="text-[0.72rem] text-[#6b5a2e] font-semibold">{total} TELEMETRY TRACKS</span>
      </div>
      <div className="flex flex-col gap-2 flex-1 min-h-0 overflow-y-auto pr-1">
        {[...present, ...optional].map((curve) => (
          <div
            key={curve}
            className="flex items-center justify-between text-sm bg-[#1c1409] px-3 py-2 rounded border border-[#4a3813] shrink-0"
          >
            <div className="flex items-center gap-2 text-[#e8ddc7]">
              <Check className="w-4 h-4 text-[#efb027]" />
              <span className="font-bold">{curve}</span>
            </div>
            <span className="text-[0.8rem] text-[#a3893f]">{CURVE_LABELS[curve] ?? curve}</span>
          </div>
        ))}
        {missing.map((curve) => (
          <div
            key={curve}
            className="flex items-center justify-between text-sm bg-[#1c1409] px-3 py-2 rounded border border-[#6b5a2e] shrink-0"
          >
            <div className="flex items-center gap-2 text-[#6b5a2e]">
              <AlertTriangle className="w-4 h-4" />
              <span className="font-bold">{curve}</span>
            </div>
            <span className="text-[0.8rem] text-[#6b5a2e]">MISSING</span>
          </div>
        ))}
      </div>
    </div>
  );
};
