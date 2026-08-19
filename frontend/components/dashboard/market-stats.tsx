'use client';

import { Activity, RefreshCw } from 'lucide-react';
import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from 'recharts';
import { cn } from '@/lib/utils';
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

// VIX sentiment bands (NSE India VIX typical ranges).
function vixColor(v: number): string {
  if (v < 13) return '#16a34a'; // calm / low volatility
  if (v < 18) return '#65a30d'; // stable
  if (v < 22) return '#ca8a04'; // elevated
  return '#dc2626'; // high fear / volatility
}

// PCR: >1 (more puts) is bullish bias, <1 is bearish bias; color accordingly.
function pcrColor(v: number): string {
  if (v >= 1) return '#16a34a';
  return '#dc2626';
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
  const advances = s.advances ?? 0;
  const declines = s.declines ?? 0;
  const unchanged = s.unchanged ?? 0;
  const total = advances + declines + unchanged || 1;
  const breadthData = [
    { name: 'Advances', value: advances, fill: '#16a34a' },
    { name: 'Declines', value: declines, fill: '#dc2626' },
    { name: 'Unchanged', value: unchanged, fill: '#94a3b8' },
  ];
  const breadthHasData = (s.advances ?? 0) + (s.declines ?? 0) + (s.unchanged ?? 0) > 0;

  const vix = s.india_vix;
  const vixHasData = vix !== null && vix !== undefined;
  const vixData = [{ name: 'India VIX', value: vixHasData ? vix : 0 }];

  const pcr = s.nifty_pcr;
  const pcrHasData = pcr !== null && pcr !== undefined;
  const pcrData = [{ name: 'NIFTY PCR', value: pcrHasData ? pcr : 0 }];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          {tile.updatedAt && `Updated ${new Date(tile.updatedAt).toLocaleTimeString('en-IN')}`}
        </span>
        {isFallback && (
          <span className="rounded bg-yellow-500/10 px-2 py-0.5 text-xs text-yellow-600">
            Live data unavailable
          </span>
        )}
      </div>

      {/* Market Breadth — horizontal stacked bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-foreground">Market Breadth</p>
          <div className="flex items-center gap-3 text-xs">
            <span className="text-green-600">▲ {s.advances != null ? s.advances.toLocaleString('en-IN') : 'N/A'}</span>
            <span className="text-red-600">▼ {s.declines != null ? s.declines.toLocaleString('en-IN') : 'N/A'}</span>
            <span className="text-muted-foreground">● {s.unchanged != null ? s.unchanged.toLocaleString('en-IN') : 'N/A'}</span>
          </div>
        </div>
        {breadthHasData ? (
          <div className="h-8 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={[{ name: 'Breadth', ...Object.fromEntries(breadthData.map((d) => [d.name, d.value])) }]}
                layout="vertical"
                margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
              >
                <XAxis type="number" hide domain={[0, total]} />
                <YAxis type="category" dataKey="name" hide />
                {breadthData.map((d) => (
                  <Bar key={d.name} dataKey={d.name} stackId="breadth" fill={d.fill} radius={0} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">Breadth unavailable</p>
        )}
      </div>

      {/* India VIX — level bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-foreground">India VIX</p>
          <div className="flex items-baseline gap-2">
            <Value value={s.india_vix} className="text-lg" />
            {s.india_vix_change_percent !== null && s.india_vix_change_percent !== undefined && (
              <span
                className={cn(
                  'text-xs font-medium',
                  s.india_vix_change_percent >= 0 ? 'text-red-600' : 'text-green-600'
                )}
              >
                {s.india_vix_change_percent >= 0 ? '+' : ''}
                {s.india_vix_change_percent.toFixed(2)}%
              </span>
            )}
          </div>
        </div>
        {vixHasData ? (
          <div className="h-3 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={vixData} layout="vertical" margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                <XAxis type="number" hide domain={[0, 30]} />
                <YAxis type="category" dataKey="name" hide />
                <ReferenceLine x={13} stroke="#94a3b8" strokeDasharray="2 2" />
                <ReferenceLine x={18} stroke="#94a3b8" strokeDasharray="2 2" />
                <ReferenceLine x={22} stroke="#94a3b8" strokeDasharray="2 2" />
                <Bar dataKey="value" radius={3}>
                  <Cell fill={vixColor(vix as number)} />
                  <LabelList dataKey="value" position="right" formatter={(v: number) => v.toFixed(2)} style={{ fontSize: 10 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">VIX unavailable</p>
        )}
      </div>

      {/* NIFTY PCR — diverging bar at 1.0 */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-foreground">NIFTY PCR</p>
          <Value value={s.nifty_pcr} className="text-lg" />
        </div>
        {pcrHasData ? (
          <div className="h-3 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={pcrData} layout="vertical" margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                <XAxis type="number" hide domain={[0, 2]} />
                <YAxis type="category" dataKey="name" hide />
                <ReferenceLine x={1} stroke="#475569" strokeWidth={1} />
                <Bar dataKey="value" radius={3}>
                  <Cell fill={pcrColor(pcr as number)} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">PCR unavailable</p>
        )}
      </div>
    </div>
  );
}

function StatsSkeleton() {
  return (
    <div className="space-y-5">
      <div className="h-3 w-24 animate-pulse rounded bg-muted" />
      <div className="space-y-2">
        <div className="h-3 w-20 animate-pulse rounded bg-muted" />
        <div className="h-8 w-full animate-pulse rounded bg-muted" />
      </div>
      <div className="space-y-2">
        <div className="h-3 w-16 animate-pulse rounded bg-muted" />
        <div className="h-3 w-full animate-pulse rounded bg-muted" />
      </div>
      <div className="space-y-2">
        <div className="h-3 w-16 animate-pulse rounded bg-muted" />
        <div className="h-3 w-full animate-pulse rounded bg-muted" />
      </div>
    </div>
  );
}

