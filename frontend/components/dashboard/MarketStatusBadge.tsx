'use client';

import { useQuery } from '@tanstack/react-query';
import { systemApi, type MarketDataStatus } from '@/lib/api';
import { IST_TIME_ZONE, parseUtc } from '@/lib/utils';

const POLL_MS = 60_000;

/**
 * Market-data status indicator (Phase 21). Shows whether the app is connected
 * to a REAL market-data provider so it is never silently on Mock/synthetic:
 *
 *   ● LIVE      yfinance — Updated 10:43:12 IST
 *   ● UNAVAILABLE  Live provider not configured
 *   ● MOCK (DEVELOPMENT MODE)
 *
 * Uses the shared React Query cache so the badge deduplicates with any other
 * component reading /market/status instead of firing an independent interval
 * per page mount.
 */
export function MarketStatusBadge() {
  const { data: status } = useQuery<MarketDataStatus>({
    queryKey: ['market', 'status'],
    queryFn: async () => {
      const s = await systemApi.marketStatus();
      if (!s) throw new Error('Market status unavailable');
      return s;
    },
    refetchInterval: POLL_MS,
    refetchOnWindowFocus: false,
  });

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
    ? parseUtc(status.last_success).toLocaleTimeString('en-IN', {
        timeZone: IST_TIME_ZONE,
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
