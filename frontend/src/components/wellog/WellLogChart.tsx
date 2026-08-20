import React, { useState } from 'react';
import { CurvePoint, WellCurves } from '../../types/wellLog';

interface WellLogChartProps {
  curves?: WellCurves | null;
  wellName: string;
}

type CurveKey = 'GR' | 'RDEP' | 'RHOB' | 'NPHI' | 'DTC';

interface TrackDef {
  key: CurveKey;
  min: number;
  max: number;
  colour: string;
  label: string;
}

const SVG_W = 340;
const SVG_H = 320;
const TOP_PAD = 15;
const BOTTOM_PAD = 25;
const PLOT_H = SVG_H - TOP_PAD - BOTTOM_PAD;
const LEFT_EDGE = 28;
const RIGHT_EDGE = 335;
const TRACK_GAP = 3;

// Scale ranges come from the training-set percentiles (p01-p99) so real North Sea
// curves fill the track instead of hugging one edge.
const TRACK_DEFS: TrackDef[] = [
  { key: 'GR', min: 0, max: 160, colour: '#efb027', label: 'GR (API)' },
  { key: 'RDEP', min: 0, max: 100, colour: '#c99a3a', label: 'RDEP (Ωm)' },
  { key: 'RHOB', min: 1.65, max: 2.95, colour: '#8a6f2c', label: 'RHOB (g/cc)' },
  { key: 'NPHI', min: 0, max: 0.7, colour: '#e0c070', label: 'NPHI (v/v)' },
  { key: 'DTC', min: 50, max: 180, colour: '#a3893f', label: 'DTC (µs/ft)' },
];

export const WellLogChart: React.FC<WellLogChartProps> = ({ curves, wellName }) => {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const points = curves?.points ?? [];
  const [startDepth, endDepth] = curves?.depth_range ?? [0, 1];
  const depthSpan = Math.max(1, endDepth - startDepth);

  // Only draw tracks the well actually carries, and share the width between them.
  const available = curves?.available_curves ?? [];
  const tracks = TRACK_DEFS.filter((t) => available.includes(t.key));
  const trackWidth = tracks.length
    ? (RIGHT_EDGE - LEFT_EDGE - TRACK_GAP * (tracks.length - 1)) / tracks.length
    : 0;

  const bounds = (index: number) => {
    const left = LEFT_EDGE + index * (trackWidth + TRACK_GAP);
    return { left, right: left + trackWidth };
  };

  const getX = (val: number | null | undefined, t: TrackDef, left: number, right: number) => {
    if (val === null || val === undefined || Number.isNaN(val)) return (left + right) / 2;
    const norm = Math.max(0, Math.min(1, (val - t.min) / (t.max - t.min)));
    return left + norm * (right - left);
  };

  const getY = (depth: number) => {
    const norm = Math.max(0, Math.min(1, (depth - startDepth) / depthSpan));
    return TOP_PAD + norm * PLOT_H;
  };

  // A gap in a curve should break the line, not draw a straight segment across it.
  const segments = (t: TrackDef, left: number, right: number) => {
    const out: string[] = [];
    let run: string[] = [];
    points.forEach((p: CurvePoint) => {
      const v = p[t.key];
      if (v === null || v === undefined || Number.isNaN(v)) {
        if (run.length > 1) out.push(run.join(' '));
        run = [];
        return;
      }
      run.push(`${getX(v, t, left, right).toFixed(1)},${getY(p.depth).toFixed(1)}`);
    });
    if (run.length > 1) out.push(run.join(' '));
    return out;
  };

  const hover = hoverIndex !== null ? points[hoverIndex] : null;

  return (
    <div className="relative bg-[#241a0a] border-2 border-[#4a3813] rounded p-2.5 mb-3 cyber-glow-amber">
      <div className="flex items-center justify-between text-xs text-[#a3893f] font-mono mb-1.5 pb-1 border-b border-[#4a3813]">
        <span className="font-bold text-[#efb027]">{wellName || '---'}</span>
        <span className="font-bold">
          {startDepth.toFixed(0)}-{endDepth.toFixed(0)}m
        </span>
      </div>

      <svg
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        className="w-full h-[320px] overflow-visible cursor-crosshair"
        onMouseLeave={() => setHoverIndex(null)}
        onMouseMove={(e) => {
          if (!points.length) return;
          const rect = e.currentTarget.getBoundingClientRect();
          const scale = rect.height / SVG_H;
          const ratio = Math.max(
            0,
            Math.min(1, (e.clientY - rect.top - TOP_PAD * scale) / (PLOT_H * scale)),
          );
          setHoverIndex(Math.round(ratio * (points.length - 1)));
        }}
      >
        <line x1={LEFT_EDGE - 3} y1={TOP_PAD} x2={LEFT_EDGE - 3} y2={TOP_PAD + PLOT_H} stroke="#4a3813" strokeWidth="1.5" />
        <line x1={RIGHT_EDGE} y1={TOP_PAD} x2={RIGHT_EDGE} y2={TOP_PAD + PLOT_H} stroke="#4a3813" strokeWidth="1.5" />

        {tracks.slice(1).map((t, i) => {
          const x = bounds(i + 1).left - TRACK_GAP / 2;
          return (
            <line key={`div-${t.key}`} x1={x} y1={TOP_PAD} x2={x} y2={TOP_PAD + PLOT_H} stroke="#4a3813" strokeWidth="1" strokeDasharray="3 3" />
          );
        })}

        {Array.from({ length: 5 }).map((_, i) => {
          const d = startDepth + (depthSpan / 4) * i;
          const y = getY(d);
          return (
            <g key={`grid-${i}`}>
              <line x1={LEFT_EDGE - 8} y1={y} x2={RIGHT_EDGE} y2={y} stroke="#4a3813" strokeWidth="0.8" opacity="0.6" />
              <text x="1" y={y + 3} fontSize="8" fill="#a3893f" fontFamily="Fira Code, monospace" fontWeight="bold">
                {d.toFixed(0)}
              </text>
            </g>
          );
        })}

        {tracks.map((t, i) => {
          const { left, right } = bounds(i);
          return segments(t, left, right).map((pts, j) => (
            <polyline key={`${t.key}-${j}`} points={pts} fill="none" stroke={t.colour} strokeWidth="1.5" />
          ));
        })}

        {hover && (
          <g>
            <line x1={LEFT_EDGE - 8} y1={getY(hover.depth)} x2={RIGHT_EDGE} y2={getY(hover.depth)} stroke="#efb027" strokeWidth="1" strokeDasharray="4 2" />
            {tracks.map((t, i) => {
              const v = hover[t.key];
              if (v === null || v === undefined) return null;
              const { left, right } = bounds(i);
              return <circle key={`hv-${t.key}`} cx={getX(v, t, left, right)} cy={getY(hover.depth)} r="2.6" fill={t.colour} />;
            })}
          </g>
        )}

        {tracks.map((t, i) => {
          const { left } = bounds(i);
          return (
            <g key={`legend-${t.key}`}>
              <rect x={left} y={SVG_H - 16} width={trackWidth} height="14" fill="#2e2308" rx="2" />
              <text
                x={left + trackWidth / 2}
                y={SVG_H - 6}
                textAnchor="middle"
                fontSize="7.5"
                fill={t.colour}
                fontWeight="bold"
                fontFamily="Fira Code, monospace"
              >
                {t.label}
              </text>
            </g>
          );
        })}
      </svg>

      {hover && (
        <div className="mt-1.5 bg-[#1c1409] border border-[#efb027] p-1.5 rounded text-[0.6rem] text-[#efb027] font-mono flex flex-wrap gap-x-3 gap-y-0.5 font-bold">
          <span>Z: {hover.depth.toFixed(1)}m</span>
          {tracks.map((t) => (
            <span key={`ro-${t.key}`} style={{ color: t.colour }}>
              {t.key}: {hover[t.key] === null || hover[t.key] === undefined ? '--' : Number(hover[t.key]).toFixed(t.key === 'RHOB' || t.key === 'NPHI' ? 2 : 1)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
