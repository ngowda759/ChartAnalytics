"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { optionsApi, type OptionAnalysis } from "@/lib/api";
import { useTileQuery } from "@/lib/useTileQuery";
import { AlertTriangle, RefreshCw } from "lucide-react";

export function OptionChainAnalysis({ symbol }: { symbol: string }) {
  const tile = useTileQuery<OptionAnalysis>(
    ["options", "analysis", symbol],
    () => optionsApi.getAnalysis(symbol),
    { refetchIntervalMs: 5 * 60 * 1000 }
  );

  if (tile.loading) {
    return <OptionChainSkeleton title={`Option Chain - ${symbol}`} />;
  }

  if (tile.error && !tile.data) {
    return (
      <OptionChainError
        title={`Option Chain - ${symbol}`}
        message="Option chain data is temporarily unavailable"
        detail="No live option data provider is configured or the market is closed."
        onRetry={tile.refetch}
      />
    );
  }

  const analysis = tile.data;
  if (!analysis) {
    return (
      <OptionChainError
        title={`Option Chain - ${symbol}`}
        message="No option chain data available"
        onRetry={tile.refetch}
      />
    );
  }

  const fmt = (n: number | undefined | null, digits = 2) =>
    n === null || n === undefined ? "N/A" : n.toFixed(digits);

  const formatOI = (oi: number) => {
    if (oi >= 10000000) return `${(oi / 10000000).toFixed(2)} Cr`;
    if (oi >= 100000) return `${(oi / 100000).toFixed(2)} L`;
    return oi.toLocaleString("en-IN");
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            Option Chain - {symbol}
            <Badge variant="outline" className="text-xs capitalize">
              {tile.source}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              label="PCR"
              value={fmt(analysis.key_metrics.pcr)}
              subtext={analysis.key_metrics.pcr > 1 ? "Bullish" : "Bearish"}
              variant={analysis.key_metrics.pcr > 1 ? "bullish" : "bearish"}
            />
            <MetricCard
              label="Max Pain"
              value={
                analysis.key_metrics.max_pain
                  ? analysis.key_metrics.max_pain.toLocaleString("en-IN")
                  : "N/A"
              }
              subtext="At Expiry"
              variant="neutral"
            />
            <MetricCard
              label="ATM IV"
              value={`${fmt(analysis.key_metrics.atm_iv, 1)}%`}
              subtext="Current Volatility"
              variant="neutral"
            />
            <MetricCard
              label="IV Skew"
              value={fmt(analysis.key_metrics.iv_skew)}
              subtext="Put/Call IV"
              variant={analysis.key_metrics.iv_skew > 1 ? "bullish" : "bearish"}
            />
          </div>

          <div className="mt-4 p-4 rounded-lg bg-accent/50">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Market Outlook</span>
              <Badge
                variant={
                  analysis.outlook.trend === "bullish"
                    ? "bullish"
                    : analysis.outlook.trend === "bearish"
                    ? "bearish"
                    : "neutral"
                }
              >
                {analysis.outlook.trend.toUpperCase()} (
                {analysis.outlook.confidence}%)
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              {analysis.outlook.interpretation}
            </p>
          </div>

          <div className="mt-4 grid grid-cols-3 gap-4 text-center">
            <div className="p-3 rounded-lg bg-red-500/10">
              <p className="text-xs text-muted-foreground mb-1">Call OI</p>
              <p className="text-lg font-bold text-red-500">
                {formatOI(analysis.oi_summary.total_call_oi)}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-green-500/10">
              <p className="text-xs text-muted-foreground mb-1">Put OI</p>
              <p className="text-lg font-bold text-green-500">
                {formatOI(analysis.oi_summary.total_put_oi)}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-blue-500/10">
              <p className="text-xs text-muted-foreground mb-1">Net OI</p>
              <p className="text-lg font-bold text-blue-500">
                {formatOI(analysis.oi_summary.net_oi)}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Support & Resistance — backend returns strike arrays. */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-green-500"></span>
              Support Levels
            </CardTitle>
          </CardHeader>
          <CardContent>
            {analysis.support_levels.length === 0 ? (
              <p className="text-sm text-muted-foreground">N/A</p>
            ) : (
              <div className="space-y-3">
                {analysis.support_levels.map((strike, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <span className="font-mono font-medium">
                      ₹{strike.toLocaleString("en-IN")}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500"></span>
              Resistance Levels
            </CardTitle>
          </CardHeader>
          <CardContent>
            {analysis.resistance_levels.length === 0 ? (
              <p className="text-sm text-muted-foreground">N/A</p>
            ) : (
              <div className="space-y-3">
                {analysis.resistance_levels.map((strike, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <span className="font-mono font-medium">
                      ₹{strike.toLocaleString("en-IN")}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  subtext,
  variant = "neutral",
}: {
  label: string;
  value: string;
  subtext: string;
  variant?: "bullish" | "bearish" | "neutral";
}) {
  return (
    <div
      className={cn(
        "p-3 rounded-lg",
        variant === "bullish" && "bg-green-500/10",
        variant === "bearish" && "bg-red-500/10",
        variant === "neutral" && "bg-muted"
      )}
    >
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p
        className={cn(
          "text-xl font-bold",
          variant === "bullish" && "text-green-500",
          variant === "bearish" && "text-red-500",
          variant === "neutral" && "text-foreground"
        )}
      >
        {value}
      </p>
      <p className="text-xs text-muted-foreground">{subtext}</p>
    </div>
  );
}

function OptionChainSkeleton({ title }: { title: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="animate-pulse space-y-4">
          <div className="h-20 bg-muted rounded"></div>
          <div className="h-40 bg-muted rounded"></div>
        </div>
      </CardContent>
    </Card>
  );
}

function OptionChainError({
  title,
  message,
  detail,
  onRetry,
}: {
  title: string;
  message: string;
  detail?: string;
  onRetry: () => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
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
      </CardContent>
    </Card>
  );
}
