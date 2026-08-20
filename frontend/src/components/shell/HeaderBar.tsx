import React, { useState, useEffect } from 'react';
import { Activity, ShieldCheck, Database, Radio } from 'lucide-react';
import { useSessionStore } from '../../stores/sessionStore';
import geoMindIcon from '../../assets/geo_mind.svg';
import petroTowerIcon from '../../assets/petro_Tower.svg';
import geoAvatarIcon from '../../assets/geo_Avatar.svg';
import { StatusDot } from '../ui/StatusDot';
import { OilPriceTicker } from './OilPriceTicker';

export const HeaderBar: React.FC = () => {
  const { llmStatus, xgboostStatus, ragStatus, toggleRag, prediction } = useSessionStore();
  const [timeStr, setTimeStr] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const d = new Date();
      setTimeStr(d.toTimeString().split(' ')[0] + '.' + Math.floor(d.getMilliseconds() / 100));
    };
    updateTime();
    const interval = setInterval(updateTime, 200);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="relative flex items-center justify-between px-4 py-2.5 bg-[#1c1409] border-b-2 border-[#4a3813] select-none h-16">
      {/* Top Left Corner Tech Accent */}
      <div className="absolute top-0 left-0 w-3.5 h-3.5 border-t-2 border-l-2 border-[#efb027]" />
      <div className="absolute top-0 right-0 w-3.5 h-3.5 border-t-2 border-r-2 border-[#efb027]" />

      {/* Brand Title with geo_mind.svg Icon */}
      <div className="flex items-center gap-3">
        <div className="relative flex items-center justify-center w-9 h-9 rounded bg-[#2e2308] border border-[#efb027] cyber-glow-amber overflow-hidden">
          <img src={geoMindIcon} alt="AEGIS Geo Mind" className="w-7 h-7 object-contain animate-cyber-pulse" />
          <span className="absolute -bottom-1 -right-1 text-[0.6rem] bg-[#efb027] text-[#1c1409] px-0.5 font-bold">HUD</span>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-[#efb027] text-lg font-bold tracking-widest uppercase font-mono cyber-glow-text">
              AEGIS-GEO-MIND
            </h1>
            <span className="text-sm text-[#a3893f]">//</span>
            <span className="text-xs sm:text-sm text-[#a3893f] font-mono tracking-wider">CONSOLE_v2.4</span>
          </div>
          <p className="text-[0.68rem] sm:text-[0.74rem] text-[#6b5a2e] tracking-widest uppercase font-mono font-semibold">
            SUBSURFACE LITHO-FACIES NEURAL ENGINE
          </p>
        </div>
      </div>

      {/* Avatar bookend, left of the telemetry readout */}
      <div className="hidden lg:flex items-center justify-center shrink-0 px-1">
        <img src={geoAvatarIcon} alt="" aria-hidden="true" className="h-10 w-auto object-contain opacity-90" />
      </div>

      {/* Center Telemetry Readout */}
      <div className="hidden lg:flex items-center gap-4 text-xs font-mono bg-[#241a0a] border border-[#4a3813] px-3.5 py-1.5 rounded">
        <div className="flex items-center gap-2 text-[#a3893f]">
          <Activity className="w-4 h-4 text-[#efb027]" />
          <span>ACTIVE WELL:</span>
          <span className="text-[#efb027] font-bold">{prediction?.well_name ?? '---'}</span>
        </div>
        <span className="text-[#4a3813]">|</span>
        <div className="flex items-center gap-2 text-[#a3893f]">
          <Radio className="w-4 h-4 text-[#efb027]" />
          <span>DEPTH RANGE:</span>
          <span className="text-[#e8ddc7] font-bold">
            {prediction ? `${prediction.depth_range[0].toFixed(0)}-${prediction.depth_range[1].toFixed(0)}m` : '---'}
          </span>
        </div>
      </div>

      {/* Drilling tower divider between the telemetry readout and the price ticker */}
      <div className="hidden xl:flex items-center justify-center shrink-0 px-1">
        <img
          src={petroTowerIcon}
          alt="Drilling tower"
          className="h-10 w-auto object-contain opacity-90"
        />
      </div>

      <OilPriceTicker />

      {/* Avatar bookend, right of the price ticker */}
      <div className="hidden xl:flex items-center justify-center shrink-0 px-1">
        <img src={geoAvatarIcon} alt="" aria-hidden="true" className="h-10 w-auto object-contain opacity-90" />
      </div>

      {/* Right Cyberpunk Status Indicators */}
      <div className="flex items-center gap-3 text-xs font-mono">
        <div className="flex items-center gap-1.5 bg-[#241a0a] border border-[#4a3813] px-3 py-1.5 rounded">
          <StatusDot active={llmStatus !== 'offline'} />
          <span className="text-[#6b5a2e]">LLM:</span>
          <span className="text-[#efb027] uppercase font-bold">{llmStatus}</span>
        </div>

        <div className="flex items-center gap-1.5 bg-[#241a0a] border border-[#4a3813] px-3 py-1.5 rounded">
          <ShieldCheck className="w-4 h-4 text-[#efb027]" />
          <span className="text-[#6b5a2e]">XGBOOST:</span>
          <span className="text-[#efb027] uppercase font-bold">{xgboostStatus}</span>
        </div>

        <button
          onClick={toggleRag}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded border transition-all ${
            ragStatus === 'ready'
              ? 'bg-[#2e2308] border-[#efb027] text-[#efb027] cyber-glow-amber'
              : 'bg-[#241a0a] border-[#4a3813] text-[#6b5a2e] hover:border-[#a3893f]'
          }`}
          title="Toggle RAG (Retrieval Augmented Generation)"
        >
          <Database className="w-4 h-4" />
          <span>RAG:</span>
          <span className="uppercase font-bold">{ragStatus}</span>
        </button>

        {/* Right side Geo Mind Icon */}
        <div className="w-8 h-8 rounded-full bg-[#2e2308] border border-[#4a3813] flex items-center justify-center p-0.5 shrink-0">
          <img src={geoMindIcon} alt="Geo Mind Emblem" className="w-full h-full object-contain" />
        </div>

        {/* Live HUD Clock */}
        <div className="hidden sm:block text-right border-l border-[#4a3813] pl-3 text-[#a3893f]">
          <span className="block text-xs sm:text-sm text-[#efb027] font-bold tracking-wider">{timeStr}</span>
          <span className="block text-[0.6rem] text-[#6b5a2e] uppercase font-semibold">UTC-5 SEC-0</span>
        </div>
      </div>
    </header>
  );
};
