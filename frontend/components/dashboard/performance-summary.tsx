'use client';

import { TrendingUp, TrendingDown, Target, Award, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

const mockPerformance = {
  totalPnl: 24500,
  winRate: 62,
  avgRiskReward: 1.85,
  totalTrades: 45,
  profitFactor: 1.72,
  maxDrawdown: 8.5,
  dailyLimit: {
    max: 5000,
    used: 1200,
  },
};

export function PerformanceSummary() {
  const metrics = [
    {
      label: 'Total P&L',
      value: mockPerformance.totalPnl,
      format: 'currency',
      icon: mockPerformance.totalPnl >= 0 ? TrendingUp : TrendingDown,
      variant: mockPerformance.totalPnl >= 0 ? 'bullish' : 'bearish',
    },
    {
      label: 'Win Rate',
      value: mockPerformance.winRate,
      format: 'percent',
      icon: Award,
      variant: mockPerformance.winRate >= 50 ? 'bullish' : 'bearish',
    },
    {
      label: 'Avg R:R',
      value: mockPerformance.avgRiskReward,
      format: 'ratio',
      icon: Target,
      variant: 'neutral',
    },
    {
      label: 'Profit Factor',
      value: mockPerformance.profitFactor,
      format: 'number',
      icon: Activity,
      variant: mockPerformance.profitFactor >= 1 ? 'bullish' : 'bearish',
    },
  ];

  return (
    <div className="space-y-6">
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
                {metric.format === 'currency' &&
                  `₹${metric.value.toLocaleString()}`}
                {metric.format === 'percent' && `${metric.value}%`}
                {metric.format === 'ratio' && `${metric.value}:1`}
                {metric.format === 'number' && metric.value}
              </p>
            </div>
          );
        })}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Daily Loss Limit</span>
          <span className="font-medium">
            ₹{mockPerformance.dailyLimit.used.toLocaleString()} / ₹
            {mockPerformance.dailyLimit.max.toLocaleString()}
          </span>
        </div>
        <Progress
          value={
            (mockPerformance.dailyLimit.used /
              mockPerformance.dailyLimit.max) *
            100
          }
          className="h-2"
        />
        <p className="text-xs text-muted-foreground">
          {mockPerformance.dailyLimit.max - mockPerformance.dailyLimit.used >
          0
            ? `₹${(
                mockPerformance.dailyLimit.max -
                mockPerformance.dailyLimit.used
              ).toLocaleString()} remaining`
            : 'Daily limit reached'}
        </p>
      </div>

      <div className="rounded-lg bg-accent p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Total Trades</p>
            <p className="text-2xl font-bold">{mockPerformance.totalTrades}</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">This Month</p>
            <p className="text-lg font-semibold">
              +{Math.round(mockPerformance.totalTrades * 0.4)}W /{' '}
              {Math.round(mockPerformance.totalTrades * 0.38)}L
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
