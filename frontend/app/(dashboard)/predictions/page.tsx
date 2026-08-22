'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  RefreshCw,
  Loader2,
  Fish,
  TrendingUp,
  TrendingDown,
  Minus,
  Users,
} from 'lucide-react';
import {
  predictionsApi,
  type PredictionListResponse,
  type SwarmDirection,
  type SwarmPrediction,
} from '@/lib/api';
import { formatISTDateTime } from '@/lib/utils';
import { toast } from 'sonner';

const REFRESH_INTERVAL_MS = 60_000;

const DIRECTION_META: Record<
  SwarmDirection,
  { label: string; variant: 'bullish' | 'bearish' | 'neutral'; icon: typeof TrendingUp }
> = {
  bullish: { label: 'Bullish', variant: 'bullish', icon: TrendingUp },
  bearish: { label: 'Bearish', variant: 'bearish', icon: TrendingDown },
  neutral: { label: 'Neutral', variant: 'neutral', icon: Minus },
};

function formatINR(value?: number | null) {
  if (value === null || value === undefined) return '—';
  return `₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(value)}`;
}

function PredictionCard({
  prediction,
  onOpen,
}: {
  prediction: SwarmPrediction;
  onOpen: (symbol: string) => void;
}) {
  const meta = DIRECTION_META[prediction.direction] ?? DIRECTION_META.neutral;
  const Icon = meta.icon;
  const unavailable = prediction.status === 'unavailable';
  return (
    <Card
      className="flex cursor-pointer flex-col transition-colors hover:bg-accent/40"
      onClick={() => onOpen(prediction.symbol)}
    >
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            {prediction.symbol}
            <Badge variant={meta.variant}>
              <Icon className="mr-1 h-3 w-3" />
              {meta.label}
            </Badge>
          </CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">{prediction.name ?? ''}</p>
        </div>
        <div className="text-right">
          <span className="text-lg font-bold">{prediction.conviction}</span>
          <p className="text-[11px] text-muted-foreground">conviction</p>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-3">
        {unavailable ? (
          <p className="text-xs text-muted-foreground">{prediction.report}</p>
        ) : (
          <>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="rounded-lg bg-accent/50 p-2">
                <div className="text-[11px] text-muted-foreground">Predicted</div>
                <div
                  className={`text-sm font-semibold ${
                    prediction.predicted_change_percent >= 0
                      ? 'text-green-600'
                      : 'text-red-600'
                  }`}
                >
                  {prediction.predicted_change_percent >= 0 ? '+' : ''}
                  {prediction.predicted_change_percent.toFixed(2)}%
                </div>
              </div>
              <div className="rounded-lg bg-accent/50 p-2">
                <div className="text-[11px] text-muted-foreground">LTP</div>
                <div className="text-sm font-semibold">
                  {formatINR(prediction.current_price)}
                </div>
              </div>
              <div className="rounded-lg bg-accent/50 p-2">
                <div className="text-[11px] text-muted-foreground">Target</div>
                <div className="text-sm font-semibold text-primary">
                  {formatINR(prediction.target_price)}
                </div>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Badge variant="outline">{prediction.horizon}</Badge>
              <Badge variant="outline">
                <Users className="mr-1 h-3 w-3" />
                {prediction.agents_bullish}↑ {prediction.agents_bearish}↓{' '}
                {prediction.agents_neutral}→
              </Badge>
              <Badge variant="outline">
                {Math.round(prediction.confidence * 100)}% confidence
              </Badge>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function PredictionsPage() {
  const [selected, setSelected] = useState<SwarmPrediction | null>(null);

  const { data, isLoading, isError, refetch, isFetching } =
    useQuery<PredictionListResponse>({
      queryKey: ['mirofish-predictions'],
      queryFn: async () => {
        const { data, error } = await predictionsApi.list(25);
        if (error || !data) throw new Error(error || 'Failed to load predictions');
        return data;
      },
      refetchInterval: REFRESH_INTERVAL_MS,
      refetchOnWindowFocus: false,
    });

  const openSymbol = async (symbol: string) => {
    const { data, error } = await predictionsApi.get(symbol);
    if (error || !data) {
      toast.error(error || 'Failed to load prediction');
      return;
    }
    setSelected(data);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <Fish className="h-7 w-7 text-primary" />
            <h1 className="text-3xl font-bold tracking-tight">Swarm Predictions</h1>
          </div>
          <p className="mt-1 text-muted-foreground">
            MiroFish-style swarm-intelligence forecasts: a population of persona
            agents simulates on the latest market seed and the emergent
            consensus becomes the prediction.
          </p>
          {data?.source && (
            <p className="mt-1 text-xs text-muted-foreground">
              Source: <span className="capitalize">{data.source}</span>
              {data.is_stale && ' (stale)'}
              {data.generated_at &&
                ` · generated ${formatISTDateTime(data.generated_at)} IST`}
            </p>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          {isFetching ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">Total</p>
            <p className="text-2xl font-bold">{data?.total ?? '—'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">Bullish</p>
            <p className="text-2xl font-bold text-green-600">
              {data?.bullish_count ?? '—'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">Bearish</p>
            <p className="text-2xl font-bold text-red-600">
              {data?.bearish_count ?? '—'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">Neutral</p>
            <p className="text-2xl font-bold text-yellow-600">
              {data?.neutral_count ?? '—'}
            </p>
          </CardContent>
        </Card>
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : isError ? (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            Failed to load swarm predictions. Click Refresh to retry.
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {(data?.results ?? []).map((p) => (
            <PredictionCard key={p.symbol} prediction={p} onOpen={openSymbol} />
          ))}
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Deterministic offline port of MiroFish (AGPL-3.0,
        github.com/666ghj/MiroFish). Educational simulation — not investment
        advice.
      </p>

      {selected && (
        <PredictionDetailModal
          prediction={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}

function PredictionDetailModal({
  prediction,
  onClose,
}: {
  prediction: SwarmPrediction;
  onClose: () => void;
}) {
  const meta = DIRECTION_META[prediction.direction] ?? DIRECTION_META.neutral;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-lg border bg-background p-6 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 className="text-xl font-bold">
              {prediction.symbol}
              {prediction.name && (
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  {prediction.name}
                </span>
              )}
            </h2>
            <p className="text-xs text-muted-foreground">
              {formatISTDateTime(prediction.timestamp)} IST ·{' '}
              <span className="capitalize">{prediction.source}</span>
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            ✕
          </Button>
        </div>

        <div className="mb-4 flex flex-wrap items-center gap-2">
          <Badge variant={meta.variant}>Direction: {meta.label}</Badge>
          <Badge variant="outline">Conviction: {prediction.conviction}/100</Badge>
          <Badge variant="outline">
            Predicted: {prediction.predicted_change_percent >= 0 ? '+' : ''}
            {prediction.predicted_change_percent.toFixed(2)}%
          </Badge>
          <Badge variant="outline">
            Confidence: {Math.round(prediction.confidence * 100)}%
          </Badge>
        </div>

        <div className="mb-5 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
          <ModalField label="Current" value={formatINR(prediction.current_price)} />
          <ModalField label="Target" value={formatINR(prediction.target_price)} />
          <ModalField
            label="Band Low"
            value={formatINR(prediction.target_low)}
          />
          <ModalField
            label="Band High"
            value={formatINR(prediction.target_high)}
          />
        </div>

        <div className="mb-5">
          <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <Users className="h-4 w-4" />
            Swarm Simulation ({prediction.agents_total} agents)
          </h3>
          <div className="space-y-1">
            {prediction.rounds.map((r) => (
              <div
                key={r.round}
                className="flex items-center gap-3 text-xs text-muted-foreground"
              >
                <span className="w-16 font-medium text-foreground">
                  Round {r.round + 1}
                </span>
                <div className="flex h-2 flex-1 overflow-hidden rounded-full bg-muted">
                  <div
                    className="bg-green-500/70"
                    style={{ width: `${r.bullish_pct}%` }}
                  />
                  <div
                    className="bg-yellow-500/70"
                    style={{ width: `${r.neutral_pct}%` }}
                  />
                  <div
                    className="bg-red-500/70"
                    style={{ width: `${r.bearish_pct}%` }}
                  />
                </div>
                <span className="w-24 text-right tabular-nums">
                  {r.bullish_pct.toFixed(0)}↑ {r.neutral_pct.toFixed(0)}→{' '}
                  {r.bearish_pct.toFixed(0)}↓
                </span>
                <span className="w-14 text-right tabular-nums">
                  {r.consensus >= 0 ? '+' : ''}
                  {r.consensus.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="mb-5">
          <h3 className="mb-2 text-sm font-semibold">Key Drivers</h3>
          <ul className="list-inside list-disc space-y-1 text-xs text-muted-foreground">
            {prediction.key_drivers.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </div>

        <p className="rounded-md border p-3 text-xs text-muted-foreground">
          {prediction.report}
        </p>
      </div>
    </div>
  );
}

function ModalField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border p-2">
      <p className="text-[10px] uppercase text-muted-foreground">{label}</p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  );
}
