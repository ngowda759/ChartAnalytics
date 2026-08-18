'use client';

import { useEffect, useState } from 'react';
import { systemApi, type MarketDataStatus } from '@/lib/api';

const POLL_MS = 60_000;

/**
 * Market-data status indicator (Phase 21). Shows whether the app is connected
 * to a REAL market-data provider so it is never silently on Mock/synthetic:
 *
 *   ● LIVE      yfinance — Updated 10:43:12 IST
 *   ● UNAVAILABLE  Live provider not configured
 *   ● MOCK (DEVELOPMENT MODE)
 */
export function MarketStatusBadge() {
  const [status, setStatus] = useState<MarketDataStatus | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const s = await systemApi.marketStatus();
        if (active) setStatus(s);
      } catch {
        if (active) setStatus(null);
      }
    };
    load();
    const id = setInterval(load, POLL_MS);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  if (!status) {
    return (
      <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
        <span className="h-2 w-2 rounded-full bg-gray-400" />
        Checking…
      </span>
    );
  }

  const dot =
    status.status === 'live'
      ? 'bg-emerald-500'
      : status.status === 'mock'
        ? 'bg-amber-500'
        : status.status === 'cached'
          ? 'bg-sky-500'
          : 'bg-red-500';
  const updated = status.last_success
    ? new Date(status.last_success).toLocaleTimeString('en-IN', {
        timeZone: 'Asia/Kolkata',
        hour12: false,
      })
    : null;

  return (
    <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
      <span className={`h-2 w-2 rounded-full ${dot}`} />
      <span className="font-medium text-foreground">
        {status.label || status.provider}
      </span>
      {updated && <span>• Updated {updated} IST</span>}
      {status.status === 'unavailable' && (
        <span className="text-red-500">Live provider not configured</span>
      )}
    </span>
  );
}
