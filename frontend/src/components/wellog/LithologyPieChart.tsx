import React from 'react';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { LithologyShare } from '../../types/prediction';
import { colourFor } from './lithologyPalette';

interface LithologyPieChartProps {
  shares: LithologyShare[];
}

// Top 4 lithologies by thickness; everything else folded into "OTHER".
export const LithologyPieChart: React.FC<LithologyPieChartProps> = ({ shares }) => {
  if (!shares.length) return null;

  const top = shares.slice(0, 4);
  const restFraction = shares.slice(4).reduce((sum, s) => sum + s.fraction, 0);
  const data = [
    ...top.map((s) => ({ name: s.lithology, value: Number((s.fraction * 100).toFixed(1)) })),
    ...(restFraction > 0.001 ? [{ name: 'OTHER', value: Number((restFraction * 100).toFixed(1)) }] : []),
  ];

  return (
    <div className="border-2 border-[#4a3813] bg-[#241a0a] rounded p-3 mb-3">
      <p className="text-[#6b5a2e] text-xs m-0 mb-2 font-mono font-bold uppercase tracking-wider">
        LITHOLOGY DISTRIBUTION
      </p>
      <div className="h-[210px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={42}
              outerRadius={88}
              paddingAngle={2}
              stroke="#1c1409"
              strokeWidth={2}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={colourFor(i)} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number, name: string) => [`${value}%`, name]}
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
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="grid grid-cols-1 gap-y-1 mt-2 text-[0.75rem] font-mono text-[#a3893f]">
        {data.map((d, i) => (
          <div key={d.name} className="flex items-center gap-1.5 truncate">
            <span
              className="w-2.5 h-2.5 rounded-sm shrink-0"
              style={{ background: colourFor(i) }}
            />
            <span className="uppercase truncate">{d.name}</span>
            <span className="text-[#e8ddc7] font-bold ml-auto">{d.value}%</span>
          </div>
        ))}
      </div>
    </div>
  );
};
