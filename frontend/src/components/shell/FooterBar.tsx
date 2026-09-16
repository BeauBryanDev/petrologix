import React from 'react';
import { HardDrive } from 'lucide-react';
import geoMindIcon from '../../assets/geo_mind.svg';
import fastAPILogo from '../../assets/FastAPI.svg';
import PythonIcon from '../../assets/Python.svg';
import ReactIcon from '../../assets/React.svg';
import SkleanIcon from '../../assets/Sklearn.svg';
import TailwindCSSIcon from '../../assets/Tailwind.svg';
import TypeScriptIcon from '../../assets/Typescript.svg';
import ViteIcon from '../../assets/Vite.svg';

import claudeMark from '../../assets/claude-logo.png';
import { SignalIndicator } from './SignalIndicator';

// Thank you all the open source contributors for making this project possible!
const BACKEND_CREDITS = [
  { src : PythonIcon , alt: 'Python', href: 'https://www.python.org/' },
  { src : SkleanIcon , alt: 'scikit-learn', href: 'https://scikit-learn.org/stable/' },
  { src : fastAPILogo, alt: 'FastAPI', href: 'https://fastapi.tiangolo.com/' },
];
// Thank you all the open source contributors for making this project possible!
const FRONTEND_CREDITS = [
  { src : ReactIcon , alt: 'React', href: 'https://reactjs.org/' },
  { src : TypeScriptIcon , alt: 'TypeScript', href: 'https://www.typescriptlang.org/' },
  { src : TailwindCSSIcon , alt: 'TailwindCSS', href: 'https://tailwindcss.com/' },
  { src : ViteIcon , alt: 'Vite', href: 'https://vitejs.dev/' },
];


type Credit = { src: string; alt: string; href: string };

const CreditStrip: React.FC<{ label: string; credits: Credit[] }> = ({ label, credits }) => (
  <div className="hidden xl:flex items-center gap-3">
    <span className="text-[#6b5a2e] text-[0.68rem] uppercase tracking-widest font-semibold">
      {label}
    </span>
    <div className="flex items-center gap-3">
      {credits.map((c) => (
        <a
          key={c.alt}
          href={c.href}
          target="_blank"
          rel="noreferrer"
          title={c.alt}
          className="w-10 h-10 rounded bg-[#241a0a] border border-[#4a3813] flex items-center justify-center hover:border-[#efb027] transition-colors"
        >
          <img src={c.src} alt={c.alt} className="w-7 h-7 object-contain" />
        </a>
      ))}
    </div>
  </div>
);

export const FooterBar: React.FC = () => {
  return (
    <footer className="relative px-5 py-2 bg-[#1c1409] border-t-[3px] border-[#efb027] flex items-center justify-between text-sm text-[#6b5a2e] font-mono h-20 select-none">
      {/* Bottom Corner Tech Accents */}
      <div className="absolute bottom-0 left-0 w-5 h-5 border-b-[3px] border-l-[3px] border-[#efb027]" />
      <div className="absolute bottom-0 right-0 w-5 h-5 border-b-[3px] border-r-[3px] border-[#efb027]" />

      {/* Purpose mark */}
      <div className="flex items-center gap-3">
        <div className="w-11 h-11 rounded bg-[#2e2308] border border-[#efb027] flex items-center justify-center shrink-0">
          <img src={geoMindIcon} alt="" aria-hidden="true" className="w-8 h-8 object-contain" />
        </div>
        <div className="leading-tight">
          <div className="text-[#efb027] font-bold tracking-widest uppercase text-[0.82rem]">
            Made for geology use
          </div>
          <div className="text-[#a3893f] tracking-wider uppercase text-[0.74rem] font-semibold">
            Well logs detection with ML
          </div>
        </div>
      </div>

      {/* Engine readout */}
      <div className="flex items-center gap-4">
        <CreditStrip label="Backend" credits={BACKEND_CREDITS} />

        <div className="flex items-center gap-2.5 bg-[#241a0a] border border-[#4a3813] px-4 py-2 rounded">
          <img src={claudeMark} alt="" aria-hidden="true" className="w-7 h-7 object-contain shrink-0" />
          <div className="leading-tight">
            <div className="text-[#6b5a2e] text-[0.68rem] uppercase tracking-wider font-semibold">
              Reasoning engine
            </div>
            <div className="text-[#efb027] font-bold tracking-wide">claude-sonnet-5</div>
          </div>
        </div>

        <CreditStrip label="Frontend" credits={FRONTEND_CREDITS} />

        <div className="hidden 2xl:flex items-center gap-2">
          <HardDrive className="w-5 h-5 text-[#6b5a2e]" />
          <span>SAMPLING:</span>
          <span className="text-[#e8ddc7] font-semibold">1.0m STEP</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <SignalIndicator />
        <span className="text-[#4a3813]">|</span>
        <span className="text-[#efb027] bg-[#2e2308] px-3 py-1.5 border border-[#efb027]/40 rounded text-[0.74rem] font-bold uppercase tracking-wider">
          RESEARCH PREVIEW
        </span>

        {/* Mirrors the mark on the left end. */}
        <div className="w-11 h-11 rounded bg-[#2e2308] border border-[#efb027] flex items-center justify-center shrink-0">
          <img src={geoMindIcon} alt="" aria-hidden="true" className="w-8 h-8 object-contain" />
        </div>
      </div>
    </footer>
  );
};
