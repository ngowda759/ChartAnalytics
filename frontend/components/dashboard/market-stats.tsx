'use client';

import { Activity, RefreshCw } from 'lucide-react';
import { cn, formatISTTime } from '@/lib/utils';
import { marketApi, type MarketStats as MarketStatsData } from '@/lib/api';
import { useTileQuery } from '@/lib/useTileQuery';

function Value({
  value,
  className,
}: {
  value: number | null | undefined;
  className?: string;
}) {
  if (value === null || value === undefined) {
    return <span className={cn('text-2xl font-bold text-muted-foreground', className)}>N/A</span>;
  }
  return <span className={cn('text-2xl font-bold', className)}>{value.toLocaleString('en-IN')}</span>;
}

export function MarketStats() {
  const tile = useTileQuery<MarketStatsData>(
    ['market', 'stats'],
    () => marketApi.getStats(),
    { refetchIntervalMs: 60 * 1000 }
  );

  if (tile.loading) {
    return <StatsSkeleton />;
  }

  if (tile.error && !tile.data) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-8 text-center">
        <Activity className="h-10 w-10 text-muted-foreground/50" />
        <div>
          <p className="text-sm font-medium">Market stats unavailable</p>
          <p className="mt-1 text-xs text-muted-foreground">{tile.error}</p>
        </div>
        <button
          onClick={tile.refetch}
          className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-accent"
        >
          <RefreshCw className="h-3 w-3" />
          Retry
        </button>
      </div>
    );
  }

  const s = tile.data;
  if (!s) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">No data available</p>
    );
  }

  const isFallback = s.source !== 'live';

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          {tile.updatedAt && `Updated ${formatISTTime(tile.updatedAt)} IST`}
        </span>
        {isFallback && (
          <span className="rounded bg-yellow-500/10 px-2 py-0.5 text-xs text-yellow-600">
            Live data unavailable
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">Market Breadth</p>
          <div className="flex items-center gap-2">
            <Value value={s.advances} className="text-green-600" />
            <span className="text-sm text-green-600">Advances</span>
          </div>
          <div className="flex items-center gap-2">
            <Value value={s.declines} className="text-red-600" />
            <span className="text-sm text-red-600">Declines</span>
          </div>
        </div>
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">Unchanged</p>
          <Value value={s.unchanged} />
        </div>
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">NIFTY PCR</p>
          <Value value={s.nifty_pcr} />
          <p className="text-xs text-muted-foreground">Open Interest Ratio</p>
        </div>
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">India VIX</p>
          <Value value={s.india_vix} />
          {s.india_vix_change_percent !== null && s.india_vix_change_percent !== undefined && (
            <p
              className={cn(
                'text-xs',
                s.india_vix_change_percent >= 0 ? 'text-red-600' : 'text-green-600'
              )}
            >
              {s.india_vix_change_percent >= 0 ? '+' : ''}
              {s.india_vix_change_percent.toFixed(2)}%
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="space-y-2">
          <div className="h-3 w-20 animate-pulse rounded bg-muted" />
          <div className="h-7 w-16 animate-pulse rounded bg-muted" />
        </div>
      ))}
    </div>
  );
}
