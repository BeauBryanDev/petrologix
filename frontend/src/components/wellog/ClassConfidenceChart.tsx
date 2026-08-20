import React from 'react';
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { LithologyShare } from '../../types/prediction';
import { colourFor } from './lithologyPalette';

interface ClassConfidenceChartProps {
  shares: LithologyShare[];
}

// Mean confidence per lithology for the top 4 by thickness.
export const ClassConfidenceChart: React.FC<ClassConfidenceChartProps> = ({ shares }) => {
  if (!shares.length) return null;

  const data = shares.slice(0, 4).map((s) => ({
    name: s.lithology.length > 10 ? `${s.lithology.slice(0, 9)}.` : s.lithology,
    full: s.lithology,
    confidence: Number((s.mean_confidence * 100).toFixed(1)),
  }));

  return (
    <div className="border-2 border-[#4a3813] bg-[#241a0a] rounded p-3 mb-3">
      <p className="text-[#6b5a2e] text-xs m-0 mb-2 font-mono font-bold uppercase tracking-wider">
        CONFIDENCE BY CLASS
      </p>
      <div className="h-[130px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -22 }}>
            <XAxis
              dataKey="name"
              tick={{ fill: '#a3893f', fontSize: 9, fontFamily: 'Fira Code, monospace' }}
              axisLine={{ stroke: '#4a3813' }}
              tickLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: '#6b5a2e', fontSize: 9, fontFamily: 'Fira Code, monospace' }}
              axisLine={{ stroke: '#4a3813' }}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: '#2e2308' }}
              formatter={(value: number, _n: string, item: { payload?: { full?: string } }) => [
                `${value}%`,
                item?.payload?.full ?? '',
              ]}
              contentStyle={{
                background: '#1c1409',
                border: '1px solid #efb027',
                borderRadius: 4,
                fontFamily: 'Fira Code, monospace',
                fontSize: 11,
              }}
              itemStyle={{ color: '#efb027' }}
              labelStyle={{ color: '#a3893f' }}
            />
            <Bar dataKey="confidence" radius={[2, 2, 0, 0]}>
              {data.map((_, i) => (
                <Cell key={i} fill={colourFor(i)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
