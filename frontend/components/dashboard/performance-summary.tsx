'use client';

import {
  TrendingUp,
  TrendingDown,
  Target,
  Award,
  Activity,
  RefreshCw,
} from 'lucide-react';
import { cn, formatISTTime } from '@/lib/utils';
import { journalApi } from '@/lib/api';
import { useTileQuery } from '@/lib/useTileQuery';

interface PerformanceMetrics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  average_win: number;
  average_loss: number;
  profit_factor: number | null;
  total_pnl: number;
  expectancy: number;
  // Non-derivable from a flat trade list; the backend returns null.
  sharpe_ratio?: number | null;
  max_drawdown?: number | null;
  avg_rr?: number | null;
  source?: string;
}

type Variant = 'bullish' | 'bearish' | 'neutral';

function MetricValue({
  value,
  format,
}: {
  value: number | null | undefined;
  format: 'currency' | 'percent' | 'ratio' | 'number';
}) {
  if (value === null || value === undefined) {
    return <span className="text-lg font-bold text-muted-foreground">N/A</span>;
  }
  return (
    <span>
      {format === 'currency' && `₹${value.toLocaleString('en-IN')}`}
      {format === 'percent' && `${value.toFixed(1)}%`}
      {format === 'ratio' && `${value.toFixed(2)}:1`}
      {format === 'number' && value.toFixed(2)}
    </span>
  );
}

export function PerformanceSummary() {
  const tile = useTileQuery<PerformanceMetrics>(
    ['journal', 'performance'],
    () => journalApi.getPerformance(),
    { refetchIntervalMs: 5 * 60 * 1000 }
  );

  if (tile.loading) {
    return <PerformanceSkeleton />;
  }

  if (tile.error && !tile.data) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-8 text-center">
        <TrendingDown className="h-10 w-10 text-muted-foreground/50" />
        <div>
          <p className="text-sm font-medium">Unable to load performance</p>
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

  const m = tile.data;
  if (!m) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No performance data available
      </p>
    );
  }

  // No stored trades yet -> truthful empty state, not fabricated metrics.
  if (!m.total_trades) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
        <TrendingDown className="h-10 w-10 text-muted-foreground/50" />
        <p className="text-sm font-medium">No trading history available</p>
        <p className="text-xs text-muted-foreground">
          Record trades in the journal to see performance metrics.
        </p>
      </div>
    );
  }

  const metrics: {
    label: string;
    value: number | null | undefined;
    format: 'currency' | 'percent' | 'ratio' | 'number';
    icon: typeof TrendingUp;
    variant: Variant;
  }[] = [
    {
      label: 'Total P&L',
      value: m.total_pnl,
      format: 'currency',
      icon: m.total_pnl >= 0 ? TrendingUp : TrendingDown,
      variant: m.total_pnl >= 0 ? 'bullish' : 'bearish',
    },
    {
      label: 'Win Rate',
      value: m.win_rate,
      format: 'percent',
      icon: Award,
      variant: m.win_rate >= 50 ? 'bullish' : 'bearish',
    },
    {
      label: 'Avg R:R',
      value: m.avg_rr ?? null,
      format: 'ratio',
      icon: Target,
      variant: 'neutral',
    },
    {
      label: 'Profit Factor',
      value: m.profit_factor,
      format: 'number',
      icon: Activity,
      variant: (m.profit_factor ?? 0) >= 1 ? 'bullish' : 'bearish',
    },
  ];

  return (
    <div className="space-y-6">
      {tile.stale && tile.updatedAt && (
        <p className="text-xs text-muted-foreground">
          Cached • Updated {formatISTTime(tile.updatedAt)} IST ago
        </p>
      )}
      <div className="grid grid-cols-2 gap-4">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          const isPositive = metric.variant === 'bullish';
          const isNegative = metric.variant === 'bearish';
          return (
            <div
              key={metric.label}
              className={cn(
                'rounded-lg border p-3',
                isPositive && 'border-green-500/20 bg-green-500/5',
                isNegative && 'border-red-500/20 bg-red-500/5',
                metric.variant === 'neutral' && 'bg-accent'
              )}
            >
              <div className="flex items-center gap-2">
                <Icon
                  className={cn(
                    'h-4 w-4',
                    isPositive && 'text-green-600',
                    isNegative && 'text-red-600',
                    !isPositive && !isNegative && 'text-muted-foreground'
                  )}
                />
                <span className="text-xs text-muted-foreground">
                  {metric.label}
                </span>
              </div>
              <p
                className={cn(
                  'mt-1 text-lg font-bold',
                  isPositive && 'text-green-600',
                  isNegative && 'text-red-600'
                )}
              >
                <MetricValue value={metric.value} format={metric.format} />
              </p>
            </div>
          );
        })}
      </div>

      <div className="rounded-lg bg-accent p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Total Trades</p>
            <p className="text-2xl font-bold">{m.total_trades}</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">Wins / Losses</p>
            <p className="text-lg font-semibold">
              {m.winning_trades}W / {m.losing_trades}L
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function PerformanceSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="rounded-lg border bg-accent p-3">
            <div className="h-3 w-20 animate-pulse rounded bg-muted" />
            <div className="mt-2 h-5 w-16 animate-pulse rounded bg-muted" />
          </div>
        ))}
      </div>
      <div className="h-16 animate-pulse rounded-lg bg-accent" />
    </div>
  );
}
