import React, { useEffect, useRef, useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface CopyButtonProps {
  text: string;
}

export const CopyButton: React.FC<CopyButtonProps> = ({ text }) => {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number>();

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // navigator.clipboard is undefined on plain-http origins other than
      // localhost, which is how this HUD gets served on the LAN.
      const area = document.createElement('textarea');
      area.value = text;
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      document.execCommand('copy');
      document.body.removeChild(area);
    }
    setCopied(true);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setCopied(false), 1800);
  };

  return (
    <button
      type="button"
      onClick={copy}
      title={copied ? 'Copied' : 'Copy answer'}
      aria-label={copied ? 'Copied' : 'Copy answer'}
      className="flex items-center gap-1 text-[0.6rem] font-bold uppercase tracking-wider
                 text-[#a3893f] hover:text-[#efb027] border border-[#4a3813]
                 hover:border-[#efb027] rounded px-1.5 py-0.5 transition-colors"
    >
      {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
      {copied ? 'COPIED' : 'COPY'}
    </button>
  );
};
