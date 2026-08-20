import React from 'react';
import { Crosshair, FileCode } from 'lucide-react';
import { useSessionStore } from '../../stores/sessionStore';
import { CornerReticles } from '../ui/CornerReticles';
import { GeoEmblem } from '../ui/GeoEmblem';
import { PanelHeader } from '../ui/PanelHeader';
import { DetectedCurves } from './DetectedCurves';
import { FormatToggle } from './FormatToggle';
import { SampleWellPicker } from './SampleWellPicker';
import { WellLogDropZone } from './WellLogDropZone';

export const WellLogInputPanel: React.FC = () => {
  const {
    prediction,
    format,
    setFormat,
    uploadFile,
    samples,
    activeSampleId,
    loadSampleWell,
    xgboostStatus,
  } = useSessionStore();

  const busy = xgboostStatus === 'computing';

  return (
    <div className="relative bg-[#1c1409] p-4 flex flex-col gap-4 h-full select-none border-r-2 border-[#4a3813]">
      <CornerReticles />

      <PanelHeader
        section="SEC-01"
        title="WELL LOG INPUT"
        right={
          <Crosshair
            className="w-4 h-4 text-[#efb027] animate-spin"
            style={{ animationDuration: '10s' }}
          />
        }
      />

      <div className="bg-[#241a0a] border border-[#4a3813] p-2.5 rounded flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 truncate">
          <FileCode className="w-4 h-4 text-[#efb027] shrink-0" />
          <span className="text-[#e8ddc7] truncate font-semibold">
            {prediction?.well_name ?? 'NO WELL LOADED'}
          </span>
        </div>
        <span className="text-[0.68rem] bg-[#2e2308] border border-[#efb027]/50 text-[#efb027] px-2 py-0.5 rounded font-bold shrink-0">
          {prediction?.n_samples ?? 0} SAMPLES
        </span>
      </div>

      <WellLogDropZone onFile={uploadFile} />
      <FormatToggle value={format} onChange={setFormat} />
      <DetectedCurves report={prediction?.curves} />

      <GeoEmblem />

      <SampleWellPicker
        samples={samples}
        activeId={activeSampleId}
        onSelect={loadSampleWell}
        disabled={busy}
      />
    </div>
  );
};
