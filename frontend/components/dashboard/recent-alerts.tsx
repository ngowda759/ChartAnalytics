'use client';

import { Bell, TrendingUp, AlertTriangle, Activity, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { alertsApi } from '@/lib/api';
import { useTileQuery } from '@/lib/useTileQuery';

interface AlertNotification {
  id: string;
  type: string;
  symbol: string;
  message: string;
  timestamp: string;
  is_read: boolean;
}

const alertIcons: Record<string, typeof TrendingUp> = {
  ema_cross: TrendingUp,
  breakout: Activity,
  oi_spike: AlertTriangle,
  pcr_shift: AlertTriangle,
};

function variantFor(type: string): 'bullish' | 'bearish' | 'neutral' {
  if (type === 'breakout' || type === 'ema_cross') return 'bullish';
  if (type === 'pcr_shift') return 'bearish';
  return 'neutral';
}

export function RecentAlerts() {
  const tile = useTileQuery<AlertNotification[]>(
    ['alerts', 'notifications'],
    () => alertsApi.getNotifications(),
    {
      refetchIntervalMs: 60 * 1000,
      select: (rows) => ({
        // Slice only; let useTileQuery derive source/stale from the real response.
        data: (rows ?? []).slice(0, 6),
      }),
    }
  );

  if (tile.loading) {
    return <AlertsSkeleton />;
  }

  if (tile.error && !tile.data) {
    return (
      <AlertError
        message="Unable to load alerts"
        detail={tile.error}
        onRetry={tile.refetch}
      />
    );
  }

  const alerts = tile.data ?? [];

  if (alerts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <Bell className="h-12 w-12 text-muted-foreground/50" />
        <p className="mt-2 text-sm text-muted-foreground">No recent alerts</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {tile.stale && tile.updatedAt && (
        <p className="text-xs text-muted-foreground">
          Showing alerts from {formatTime(new Date(tile.updatedAt))} (stale)
        </p>
      )}
      {alerts.map((alert) => {
        const Icon = alertIcons[alert.type] ?? AlertTriangle;
        const variant = variantFor(alert.type);
        return (
          <div
            key={alert.id}
            className={cn(
              'flex items-start gap-3 rounded-lg border p-3 transition-colors',
              alert.is_read ? 'bg-card' : 'bg-accent/50 border-primary/20'
            )}
          >
            <div
              className={cn(
                'flex h-8 w-8 items-center justify-center rounded-full',
                variant === 'bullish'
                  ? 'bg-green-500/10 text-green-600'
                  : variant === 'bearish'
                  ? 'bg-red-500/10 text-red-600'
                  : 'bg-yellow-500/10 text-yellow-600'
              )}
            >
              <Icon className="h-4 w-4" />
            </div>
            <div className="flex-1 space-y-1">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">{alert.symbol}</p>
                <span className="text-xs text-muted-foreground">
                  {formatTime(new Date(alert.timestamp))}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">{alert.message}</p>
            </div>
            {!alert.is_read && (
              <span className="h-2 w-2 rounded-full bg-primary" />
            )}
          </div>
        );
      })}
    </div>
  );
}

function AlertsSkeleton() {
  return (
    <div className="space-y-3">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="flex items-start gap-3 rounded-lg border p-3"
        >
          <div className="h-8 w-8 animate-pulse rounded-full bg-muted" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-24 animate-pulse rounded bg-muted" />
            <div className="h-3 w-full animate-pulse rounded bg-muted" />
          </div>
        </div>
      ))}
    </div>
  );
}

function AlertError({
  message,
  detail,
  onRetry,
}: {
  message: string;
  detail?: string;
  onRetry: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8 text-center">
      <AlertTriangle className="h-10 w-10 text-muted-foreground/50" />
      <div>
        <p className="text-sm font-medium">{message}</p>
        {detail && (
          <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
        )}
      </div>
      <button
        onClick={onRetry}
        className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-accent"
      >
        <RefreshCw className="h-3 w-3" />
        Retry
      </button>
    </div>
  );
}

function formatTime(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  return date.toLocaleDateString('en-IN');
}
