import React, { useEffect, useState } from 'react';
import { TrendingUp } from 'lucide-react';
import { getOilPrices } from '../../services/api';
import { OilPrices } from '../../types/market';

// EIA publishes spot prices on a lag of several days, so the quote date is
// shown rather than implying a live tick.
const REFRESH_MS = 15 * 60 * 1000;

export const OilPriceTicker: React.FC = () => {
  const [prices, setPrices] = useState<OilPrices | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const data = await getOilPrices();
        if (cancelled) return;
        setPrices(data);
        setFailed(false);
      } catch {
        // Keep the last good quote on screen; only show OFFLINE if we never got one.
        if (!cancelled) setFailed(true);
      }
    };

    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const unavailable = failed && !prices;

  return (
    <div
      className="hidden xl:flex items-center gap-4 text-sm font-mono bg-[#241a0a] border border-[#4a3813] px-4 py-2.5 rounded"
      title={
        prices
          ? `EIA spot prices, quoted ${prices.wti_date}. Fetched ${new Date(prices.fetched_at).toLocaleString()}.`
          : 'EIA spot prices'
      }
    >
      <TrendingUp className="w-6 h-6 text-[#efb027]" />

      <div className="flex items-center gap-2 text-[#a3893f]">
        <span className="text-[#6b5a2e]">WTI:</span>
        <span className="text-[#efb027] font-bold text-lg tracking-tight">
          {prices ? `$${prices.wti_usd.toFixed(2)}` : unavailable ? '---' : '...'}
        </span>
      </div>

      <span className="text-[#4a3813]">|</span>

      <div className="flex items-center gap-2 text-[#a3893f]">
        <span className="text-[#6b5a2e]">BRENT:</span>
        <span className="text-[#efb027] font-bold text-lg tracking-tight">
          {prices ? `$${prices.brent_usd.toFixed(2)}` : unavailable ? '---' : '...'}
        </span>
      </div>

      <span className="text-[0.7rem] text-[#6b5a2e] uppercase tracking-wider border-l border-[#4a3813] pl-2.5">
        {unavailable ? 'EIA OFFLINE' : prices ? prices.wti_date : 'EIA'}
      </span>
    </div>
  );
};
