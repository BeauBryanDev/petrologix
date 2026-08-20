import React from 'react';
import { Badge } from './Badge';

interface PanelHeaderProps {
  section: string;
  title: string;
  right?: React.ReactNode;
  className?: string;
}

// "SEC-0X | TITLE" bar at the top of each panel.
export const PanelHeader: React.FC<PanelHeaderProps> = ({ section, title, right, className = '' }) => (
  <div className={`flex items-center justify-between pb-2 border-b border-[#4a3813] ${className}`}>
    <div className="flex items-center gap-2">
      <Badge>{section}</Badge>
      <p className="text-[#efb027] text-sm font-mono font-bold tracking-wider uppercase">{title}</p>
    </div>
    {right}
  </div>
);
