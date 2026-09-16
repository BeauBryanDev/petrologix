import React, { useState, useEffect } from 'react';
import { Activity, ShieldCheck, Database, Radio } from 'lucide-react';
import { useSessionStore } from '../../stores/sessionStore';
import geoMindIcon from '../../assets/geo_mind.svg';
import geologyIcon from '../../assets/geology_icon.svg';
import petroTowerIcon from '../../assets/petro_Tower.svg';
import geoAvatarIcon from '../../assets/geo_Avatar.svg';
import claudeMark from '../../assets/claude-logo.png';
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
    <header className="relative flex items-center justify-between px-5 py-3 bg-[#1c1409] border-b-[3px] border-[#efb027] select-none h-24">
      {/* Top Left Corner Tech Accent */}
      <div className="absolute top-0 left-0 w-5 h-5 border-t-[3px] border-l-[3px] border-[#efb027]" />
      <div className="absolute top-0 right-0 w-5 h-5 border-t-[3px] border-r-[3px] border-[#efb027]" />

      {/* Brand Title with geology_icon.svg */}
      <div className="flex items-center gap-3.5">
        <div className="relative flex items-center justify-center w-16 h-16 rounded bg-[#2e2308] border border-[#efb027] cyber-glow-amber overflow-hidden shrink-0">
          <img src={geologyIcon} alt="Petrologix" className="w-14 h-14 object-contain animate-cyber-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[#efb027] text-2xl font-bold tracking-widest uppercase font-mono cyber-glow-text">
              PETROLOGIX
            </h1>
            <span className="flex items-center gap-2 border-l border-[#4a3813] pl-3">
              <img src={claudeMark} alt="" aria-hidden="true" className="w-8 h-8 object-contain" />
              <span className="text-[0.8rem] text-[#c9a961] font-mono tracking-widest uppercase font-semibold">
                Powered by Claude
              </span>
            </span>
          </div>
          <p className="text-[0.78rem] sm:text-[0.85rem] text-[#6b5a2e] tracking-widest uppercase font-mono font-semibold">
            SUBSURFACE LITHO-FACIES NEURAL ENGINE
          </p>
        </div>
      </div>

      {/* Avatar bookend, left of the telemetry readout */}
      <div className="hidden lg:flex items-center justify-center shrink-0 px-1">
        <img src={geoAvatarIcon} alt="" aria-hidden="true" className="h-14 w-auto object-contain opacity-90" />
      </div>

      {/* Center Telemetry Readout */}
      <div className="hidden lg:flex items-center gap-4 text-sm font-mono bg-[#241a0a] border border-[#4a3813] px-4 py-2.5 rounded">
        <div className="flex items-center gap-2 text-[#a3893f]">
          <Activity className="w-5 h-5 text-[#efb027]" />
          <span>ACTIVE WELL:</span>
          <span className="text-[#efb027] font-bold">{prediction?.well_name ?? '---'}</span>
        </div>
        <span className="text-[#4a3813]">|</span>
        <div className="flex items-center gap-2 text-[#a3893f]">
          <Radio className="w-5 h-5 text-[#efb027]" />
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
          className="h-14 w-auto object-contain opacity-90"
        />
      </div>

      <OilPriceTicker />

      {/* Avatar bookend, right of the price ticker */}
      <div className="hidden xl:flex items-center justify-center shrink-0 px-1">
        <img src={geoAvatarIcon} alt="" aria-hidden="true" className="h-14 w-auto object-contain opacity-90" />
      </div>

      {/* Right Cyberpunk Status Indicators */}
      <div className="flex items-center gap-3 text-sm font-mono">
        <div className="flex items-center gap-2 bg-[#241a0a] border border-[#4a3813] px-3.5 py-2.5 rounded">
          <StatusDot active={llmStatus !== 'offline'} />
          <span className="text-[#6b5a2e]">LLM:</span>
          <span className="text-[#efb027] uppercase font-bold">{llmStatus}</span>
        </div>

        <div className="flex items-center gap-2 bg-[#241a0a] border border-[#4a3813] px-3.5 py-2.5 rounded">
          <ShieldCheck className="w-5 h-5 text-[#efb027]" />
          <span className="text-[#6b5a2e]">XGBOOST:</span>
          <span className="text-[#efb027] uppercase font-bold">{xgboostStatus}</span>
        </div>

        <button
          onClick={toggleRag}
          className={`flex items-center gap-2 px-3.5 py-2.5 rounded border transition-all ${
            ragStatus === 'ready'
              ? 'bg-[#2e2308] border-[#efb027] text-[#efb027] cyber-glow-amber'
              : 'bg-[#241a0a] border-[#4a3813] text-[#6b5a2e] hover:border-[#a3893f]'
          }`}
          title="Toggle RAG (Retrieval Augmented Generation)"
        >
          <Database className="w-5 h-5" />
          <span>RAG:</span>
          <span className="uppercase font-bold">{ragStatus}</span>
        </button>

        {/* Right side Geo Mind Icon */}
        <div className="w-11 h-11 rounded-full bg-[#2e2308] border border-[#4a3813] flex items-center justify-center p-0.5 shrink-0">
          <img src={geoMindIcon} alt="Geo Mind Emblem" className="w-full h-full object-contain" />
        </div>

        {/* Live HUD Clock */}
        <div className="hidden sm:block text-right border-l border-[#4a3813] pl-3 text-[#a3893f]">
          <span className="block text-sm sm:text-base text-[#efb027] font-bold tracking-wider">{timeStr}</span>
          <span className="block text-[0.68rem] text-[#6b5a2e] uppercase font-semibold">UTC-5 SEC-0</span>
        </div>
      </div>
    </header>
  );
};
