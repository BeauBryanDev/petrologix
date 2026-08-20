import React from 'react';
import { Activity, AlertTriangle } from 'lucide-react';
import { useSessionStore } from '../../stores/sessionStore';
import { CornerReticles } from '../ui/CornerReticles';
import { PanelHeader } from '../ui/PanelHeader';
import xgboostIcon from '../../assets/xgboost.svg';
import { ClassConfidenceChart } from './ClassConfidenceChart';
import { ConfidenceBar } from './ConfidenceBar';
import { FaciesResult } from './FaciesResult';
import { LithologyPieChart } from './LithologyPieChart';
import { WellLogChart } from './WellLogChart';

export const WellLogPlotPanel: React.FC = () => {
  const { prediction, modelInfo } = useSessionStore();
  const shares = prediction?.distribution_by_lithology ?? [];
  const refused = prediction?.distribution.status === 'out_of_distribution';

  return (
    <div className="relative bg-[#1c1409] p-4 flex flex-col justify-between h-full select-none border-l-2 border-[#4a3813]">
      <CornerReticles />

      <div>
        <PanelHeader
          section="SEC-03"
          title="SUBSURFACE TELEMETRY"
          className="mb-3"
          right={<Activity className="w-4 h-4 text-[#efb027]" />}
        />

        <WellLogChart curves={prediction?.curve_data} wellName={prediction?.well_name ?? ''} />

        {refused && (
          <div className="border-2 border-[#efb027] bg-[#2e2308] rounded p-3 mb-3 flex gap-2">
            <AlertTriangle className="w-4 h-4 text-[#efb027] shrink-0 mt-0.5" />
            <p className="text-[#e8ddc7] text-[0.74rem] font-mono m-0 leading-relaxed">
              {prediction?.distribution.message}
            </p>
          </div>
        )}

        <FaciesResult top={shares[0]} />
        <ConfidenceBar shares={shares} />
        <div className="grid grid-cols-2 gap-3">
          <LithologyPieChart shares={shares} />
          <ClassConfidenceChart shares={shares} />
        </div>

        <div className="bg-[#241a0a] border border-[#4a3813] p-2.5 rounded flex items-center justify-between text-xs">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded bg-[#2e2308] border border-[#efb027]/40 flex items-center justify-center p-0.5 shrink-0">
              <img src={xgboostIcon} alt="XGBoost Engine" className="w-full h-full object-contain" />
            </div>
            <div>
              <div className="text-[#efb027] font-bold text-xs uppercase tracking-wider font-mono">
                XGBOOST CLASSIFIER
              </div>
              <div className="text-[#6b5a2e] text-[0.68rem] font-mono font-semibold">
                {modelInfo ? `${modelInfo.n_features} features / ${modelInfo.classes.length} classes` : 'Gradient Boosted Tree'}
              </div>
            </div>
          </div>
          <span className="text-[0.6rem] bg-[#2e2308] border border-[#efb027] text-[#efb027] px-2 py-0.5 rounded font-mono font-bold uppercase">
            {prediction?.model_version ?? 'ACTIVE'}
          </span>
        </div>
      </div>
    </div>
  );
};
