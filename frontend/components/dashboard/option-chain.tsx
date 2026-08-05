"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface OptionChainAnalysis {
  symbol: string;
  spot_price: number;
  expiry_date: string;
  key_metrics: {
    pcr: number;
    pcr_change: number;
    max_pain: number;
    atm_iv: number;
    iv_skew: number;
  };
  oi_summary: {
    total_call_oi: number;
    total_put_oi: number;
    net_oi: number;
  };
  outlook: {
    trend: string;
    confidence: number;
    interpretation: string;
  };
  support_levels: Array<{ strike: number; oi: number; strength: number }>;
  resistance_levels: Array<{ strike: number; oi: number; strength: number }>;
}

export function OptionChainAnalysis({ symbol }: { symbol: string }) {
  const [analysis, setAnalysis] = useState<OptionChainAnalysis | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOptionChain();
    const interval = setInterval(fetchOptionChain, 300000); // Refresh every 5 minutes
    return () => clearInterval(interval);
  }, [symbol]);

  const fetchOptionChain = async () => {
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${baseUrl}/api/options/analysis/${encodeURIComponent(symbol)}`);
      if (response.ok) {
        const data = await response.json();
        setAnalysis(data);
      }
    } catch (error) {
      console.error("Failed to fetch option chain:", error);
      setAnalysis(getMockAnalysis(symbol));
    } finally {
      setLoading(false);
    }
  };

  const getMockAnalysis = (sym: string): OptionChainAnalysis => ({
    symbol: sym,
    spot_price: 24567.85,
    expiry_date: new Date().toISOString(),
    key_metrics: {
      pcr: 1.15,
      pcr_change: 0.05,
      max_pain: 24500,
      atm_iv: 16.5,
      iv_skew: 1.12,
    },
    oi_summary: {
      total_call_oi: 12500000,
      total_put_oi: 14375000,
      net_oi: 1875000,
    },
    outlook: {
      trend: "bullish",
      confidence: 68,
      interpretation: "PCR of 1.15 suggests bullish sentiment with hedging activity",
    },
    support_levels: [
      { strike: 24400, oi: 2500000, strength: 85 },
      { strike: 24250, oi: 1800000, strength: 70 },
      { strike: 24100, oi: 1200000, strength: 55 },
      { strike: 24000, oi: 800000, strength: 40 },
    ],
    resistance_levels: [
      { strike: 24700, oi: 2800000, strength: 80 },
      { strike: 24850, oi: 1900000, strength: 65 },
      { strike: 25000, oi: 1400000, strength: 50 },
      { strike: 25150, oi: 900000, strength: 35 },
    ],
  });

  const formatOI = (oi: number) => {
    if (oi >= 10000000) return `${(oi / 10000000).toFixed(2)} Cr`;
    if (oi >= 100000) return `${(oi / 100000).toFixed(2)} L`;
    return oi.toLocaleString();
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Option Chain Analysis</CardTitle>
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

  if (!analysis) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Option Chain Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Unable to load option chain data</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Option Chain - {symbol}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              label="PCR"
              value={analysis.key_metrics.pcr.toFixed(2)}
              subtext={analysis.key_metrics.pcr > 1 ? "Bullish" : "Bearish"}
              variant={analysis.key_metrics.pcr > 1 ? "bullish" : "bearish"}
            />
            <MetricCard
              label="Max Pain"
              value={analysis.key_metrics.max_pain.toLocaleString("en-IN")}
              subtext="At Expiry"
              variant="neutral"
            />
            <MetricCard
              label="ATM IV"
              value={`${analysis.key_metrics.atm_iv.toFixed(1)}%`}
              subtext="Current Volatility"
              variant="neutral"
            />
            <MetricCard
              label="IV Skew"
              value={analysis.key_metrics.iv_skew.toFixed(2)}
              subtext="Put/Call IV"
              variant={analysis.key_metrics.iv_skew > 1 ? "bullish" : "bearish"}
            />
          </div>

          {/* Outlook */}
          <div className="mt-4 p-4 rounded-lg bg-accent/50">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Market Outlook</span>
              <Badge
                variant={analysis.outlook.trend === "bullish" ? "bullish" : analysis.outlook.trend === "bearish" ? "bearish" : "neutral"}
              >
                {analysis.outlook.trend.toUpperCase()} ({analysis.outlook.confidence}%)
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{analysis.outlook.interpretation}</p>
          </div>

          {/* OI Summary */}
          <div className="mt-4 grid grid-cols-3 gap-4 text-center">
            <div className="p-3 rounded-lg bg-red-500/10">
              <p className="text-xs text-muted-foreground mb-1">Call OI</p>
              <p className="text-lg font-bold text-red-500">{formatOI(analysis.oi_summary.total_call_oi)}</p>
            </div>
            <div className="p-3 rounded-lg bg-green-500/10">
              <p className="text-xs text-muted-foreground mb-1">Put OI</p>
              <p className="text-lg font-bold text-green-500">{formatOI(analysis.oi_summary.total_put_oi)}</p>
            </div>
            <div className="p-3 rounded-lg bg-blue-500/10">
              <p className="text-xs text-muted-foreground mb-1">Net OI</p>
              <p className="text-lg font-bold text-blue-500">{formatOI(analysis.oi_summary.net_oi)}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Support & Resistance */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Support Levels */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-green-500"></span>
              Support Levels
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {analysis.support_levels.map((level, i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="font-mono font-medium">
                    ₹{level.strike.toLocaleString("en-IN")}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      {formatOI(level.oi)} OI
                    </span>
                    <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500"
                        style={{ width: `${level.strength}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Resistance Levels */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500"></span>
              Resistance Levels
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {analysis.resistance_levels.map((level, i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="font-mono font-medium">
                    ₹{level.strike.toLocaleString("en-IN")}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      {formatOI(level.oi)} OI
                    </span>
                    <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-red-500"
                        style={{ width: `${level.strength}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
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
    <div className={cn(
      "p-3 rounded-lg",
      variant === "bullish" && "bg-green-500/10",
      variant === "bearish" && "bg-red-500/10",
      variant === "neutral" && "bg-muted"
    )}>
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className={cn(
        "text-xl font-bold",
        variant === "bullish" && "text-green-500",
        variant === "bearish" && "text-red-500",
        variant === "neutral" && "text-foreground"
      )}>
        {value}
      </p>
      <p className="text-xs text-muted-foreground">{subtext}</p>
    </div>
  );
}
