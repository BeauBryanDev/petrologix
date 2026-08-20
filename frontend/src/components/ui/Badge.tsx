import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'solid' | 'outline';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'solid', className = '' }) => {
  const styles =
    variant === 'solid'
      ? 'bg-[#efb027] text-[#1c1409]'
      : 'bg-[#2e2308] border border-[#efb027] text-[#efb027]';
  return (
    <span className={`text-[0.68rem] px-1.5 py-0.5 rounded font-mono font-bold uppercase ${styles} ${className}`}>
      {children}
    </span>
  );
};
