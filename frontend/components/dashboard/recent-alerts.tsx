'use client';

import { Bell, TrendingUp, AlertTriangle, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

const mockAlerts = [
  {
    id: '1',
    type: 'ema_cross',
    symbol: 'NIFTY',
    message: 'NIFTY crossed above 20 EMA',
    timestamp: new Date(Date.now() - 5 * 60 * 1000),
    isRead: false,
    variant: 'bullish' as const,
  },
  {
    id: '2',
    type: 'breakout',
    symbol: 'BANKNIFTY',
    message: 'Resistance breakout at 52,800',
    timestamp: new Date(Date.now() - 15 * 60 * 1000),
    isRead: false,
    variant: 'bullish' as const,
  },
  {
    id: '3',
    type: 'oi_spike',
    symbol: 'RELIANCE',
    message: 'OI buildup detected - 25% increase',
    timestamp: new Date(Date.now() - 30 * 60 * 1000),
    isRead: true,
    variant: 'neutral' as const,
  },
  {
    id: '4',
    type: 'pcr_shift',
    symbol: 'NIFTY',
    message: 'PCR shifted from 0.8 to 1.2',
    timestamp: new Date(Date.now() - 45 * 60 * 1000),
    isRead: true,
    variant: 'bearish' as const,
  },
];

const alertIcons = {
  ema_cross: TrendingUp,
  breakout: Activity,
  oi_spike: AlertTriangle,
  pcr_shift: AlertTriangle,
};

export function RecentAlerts() {
  return (
    <div className="space-y-4">
      {mockAlerts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Bell className="h-12 w-12 text-muted-foreground/50" />
          <p className="mt-2 text-sm text-muted-foreground">No recent alerts</p>
        </div>
      ) : (
        <div className="space-y-3">
          {mockAlerts.map((alert) => {
            const Icon = alertIcons[alert.type as keyof typeof alertIcons];
            return (
              <div
                key={alert.id}
                className={cn(
                  'flex items-start gap-3 rounded-lg border p-3 transition-colors',
                  alert.isRead
                    ? 'bg-card'
                    : 'bg-accent/50 border-primary/20'
                )}
              >
                <div
                  className={cn(
                    'flex h-8 w-8 items-center justify-center rounded-full',
                    alert.variant === 'bullish'
                      ? 'bg-green-500/10 text-green-600'
                      : alert.variant === 'bearish'
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
                      {formatTime(alert.timestamp)}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">{alert.message}</p>
                </div>
                {!alert.isRead && (
                  <span className="h-2 w-2 rounded-full bg-primary" />
                )}
              </div>
            );
          })}
        </div>
      )}
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
