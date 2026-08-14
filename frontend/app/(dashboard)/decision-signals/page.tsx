'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, Target, ShieldCheck, TrendingUp, Activity, Filter } from 'lucide-react';
import {
  decisionSignalsApi,
  type DecisionAction,
  type DecisionSignal,
} from '@/lib/api';

const REFRESH_INTERVAL_MS = 60_000;

const ACTION_META: Record<
  DecisionAction,
  { label: string; variant: 'bullish' | 'neutral' | 'bearish' }
> = {
  buy: { label: 'BUY', variant: 'bullish' },
  hold: { label: 'HOLD', variant: 'neutral' },
  avoid: { label: 'AVOID', variant: 'bearish' },
};

function formatINR(value?: number | null) {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('en-IN', {
    maximumFractionDigits: 2,
  }).format(value);
}

function ScorePill({ score }: { score: number }) {
  const tone =
    score >= 70
      ? 'text-green-600'
      : score >= 45
        ? 'text-yellow-600'
        : 'text-red-600';
  return (
    <span className={`text-lg font-bold ${tone}`}>{score}</span>
  );
}

function SignalCard({ signal }: { signal: DecisionSignal }) {
  const meta = ACTION_META[signal.action] ?? ACTION_META.hold;
  return (
    <Card className="flex flex-col">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            {signal.symbol}
            <Badge variant={meta.variant}>{meta.label}</Badge>
          </CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            {signal.display_name} · {signal.category}
          </p>
        </div>
        <div className="text-right">
          <ScorePill score={signal.score} />
          <p className="text-[11px] text-muted-foreground">score</p>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-3">
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-lg bg-accent/50 p-2">
            <div className="flex items-center justify-center gap-1 text-[11px] text-muted-foreground">
              <TrendingUp className="h-3 w-3" /> Entry
            </div>
            <div className="text-sm font-semibold">
              ₹{formatINR(signal.entry)}
            </div>
          </div>
          <div className="rounded-lg bg-accent/50 p-2">
            <div className="flex items-center justify-center gap-1 text-[11px] text-muted-foreground">
              <ShieldCheck className="h-3 w-3" /> Stop
            </div>
            <div className="text-sm font-semibold text-red-600">
              ₹{formatINR(signal.stop_loss)}
            </div>
          </div>
          <div className="rounded-lg bg-accent/50 p-2">
            <div className="flex items-center justify-center gap-1 text-[11px] text-muted-foreground">
              <Target className="h-3 w-3" /> Target
            </div>
            <div className="text-sm font-semibold text-green-600">
              ₹{formatINR(signal.target)}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Badge variant="outline" className="capitalize">
            {signal.horizon}
          </Badge>
          {signal.risk_reward !== null && signal.risk_reward !== undefined && (
            <Badge variant="outline">R:R {signal.risk_reward}</Badge>
          )}
          <Badge variant="outline">
            <Activity className="mr-1 h-3 w-3" />
            {Math.round(signal.confidence * 100)}% match
          </Badge>
        </div>

        {signal.reasons.length > 0 && (
          <ul className="mt-1 list-inside list-disc space-y-1 text-xs text-muted-foreground">
            {signal.reasons.slice(0, 3).map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export default function DecisionSignalsPage() {
  const [actionFilter, setActionFilter] = useState<DecisionAction | 'all'>('all');
  const [strategyFilter, setStrategyFilter] = useState<string>('all');

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['decision-signals'],
    queryFn: async () => {
      const { data, error } = await decisionSignalsApi.listSignals({ limit: 150 });
      if (error || !data) throw new Error(error || 'Failed to load signals');
      return data;
    },
    refetchInterval: REFRESH_INTERVAL_MS,
    refetchOnWindowFocus: false,
  });

  const { data: strategies } = useQuery({
    queryKey: ['decision-signals-strategies'],
    queryFn: async () => {
      const { data, error } = await decisionSignalsApi.getStrategies();
      if (error || !data) return [];
      return data;
    },
    staleTime: 5 * 60_000,
  });

  const filtered = useMemo(() => {
    if (!data) return [];
    return data.signals.filter((s) => {
      if (actionFilter !== 'all' && s.action !== actionFilter) return false;
      if (strategyFilter !== 'all' && s.strategy !== strategyFilter) return false;
      return true;
    });
  }, [data, actionFilter, strategyFilter]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Decision Signals</h1>
          <p className="mt-1 text-muted-foreground">
            Scored, actionable trade ideas from strategy templates — action, score,
            entry / stop / target and matched reasons per symbol.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">Total signals</p>
            <p className="text-2xl font-bold">{data?.total ?? '—'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">Buy</p>
            <p className="text-2xl font-bold text-green-600">{data?.buy_count ?? '—'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">Hold</p>
            <p className="text-2xl font-bold text-yellow-600">{data?.hold_count ?? '—'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">Avoid</p>
            <p className="text-2xl font-bold text-red-600">{data?.avoid_count ?? '—'}</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Action:</span>
        </div>
        {(['all', 'buy', 'hold', 'avoid'] as const).map((a) => (
          <Button
            key={a}
            variant={actionFilter === a ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActionFilter(a)}
            className="capitalize"
          >
            {a}
          </Button>
        ))}
        <div className="mx-2 hidden h-6 w-px bg-border md:block" />
        <span className="text-sm font-medium">Strategy:</span>
        <select
          value={strategyFilter}
          onChange={(e) => setStrategyFilter(e.target.value)}
          className="rounded-md border border-input bg-background px-2 py-1 text-sm"
        >
          <option value="all">All strategies</option>
          {(strategies ?? []).map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">Loading decision signals…</p>
      ) : isError ? (
        <p className="text-red-600">Failed to load decision signals.</p>
      ) : filtered.length === 0 ? (
        <p className="text-muted-foreground">No signals match the current filters.</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((s) => (
            <SignalCard key={s.id} signal={s} />
          ))}
        </div>
      )}
    </div>
  );
}
