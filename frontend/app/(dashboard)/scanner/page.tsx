'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';
import { scannerApi } from '@/lib/api';
import { formatISTTime } from '@/lib/utils';

interface ScanResult {
  id: string;
  symbol: string;
  name?: string | null;
  scan_type: string;
  direction: 'bullish' | 'bearish' | 'neutral';
  confidence: number;
  price: number;
  change_percent: number;
  volume_ratio?: number | null;
  details?: {
    atr?: number | null;
    volume_ratio?: number | null;
    change_percent?: number | null;
    rsi?: number | null;
    ema?: number | null;
    [key: string]: unknown;
  } | null;
  timestamp: string;
  source?: string | null;
  status?: string | null;
}

const SCAN_TYPE_LABELS: Record<string, string> = {
  breakout: 'Breakout',
  ema_cross: 'EMA Cross',
  volume_spike: 'Volume Spike',
  rsi_extreme: 'RSI Extreme',
  ma_cross: 'MA Cross',
  oi_buildup: 'OI Buildup',
};

export default function ScannerPage() {
  const [results, setResults] = useState<ScanResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');
  const [scanType, setScanType] = useState<string>('all');
  const [lastScan, setLastScan] = useState<Date | null>(null);

  const runScan = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await scannerApi.getScanResults();
    if (res.error || !res.data) {
      setError(res.error ?? 'Scanner data unavailable');
      setResults([]);
    } else {
      setResults(res.data as ScanResult[]);
      setLastScan(new Date());
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    runScan();
  }, [runScan]);

  const filteredResults = results.filter((r) => {
    if (filter !== 'all' && r.direction !== filter) return false;
    if (scanType !== 'all' && r.scan_type !== scanType) return false;
    return true;
  });

  const bullishCount = results.filter((r) => r.direction === 'bullish').length;
  const bearishCount = results.filter((r) => r.direction === 'bearish').length;
  const neutralCount = results.filter((r) => r.direction === 'neutral').length;

  const getDirectionBadge = (direction: ScanResult['direction']) => {
    switch (direction) {
      case 'bullish':
        return <Badge variant="default" className="bg-green-500">Bullish</Badge>;
      case 'bearish':
        return <Badge variant="destructive">Bearish</Badge>;
      default:
        return <Badge variant="secondary">Neutral</Badge>;
    }
  };

  const getScanTypeLabel = (type: string) => SCAN_TYPE_LABELS[type] || type;

  const formatINR = (num: number) =>
    new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Market Scanner</h1>
          <p className="text-muted-foreground">
            Find trading opportunities in real-time
            {lastScan && (
              <span className="ml-2 text-xs">
                • Last scan: {formatISTTime(lastScan)} IST
              </span>
            )}
            {results[0]?.source && (
              <span className="ml-2 text-xs capitalize">
                • Source: {results[0].source}
              </span>
            )}
          </p>
        </div>
        <Button onClick={runScan} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Run Scan
        </Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Total Signals</p>
            <p className="text-2xl font-bold">{results.length}</p>
          </CardContent>
        </Card>
        <Card className="bg-green-500/5">
          <CardContent className="p-4">
            <p className="text-xs text-green-600">Bullish</p>
            <p className="text-2xl font-bold text-green-600">{bullishCount}</p>
          </CardContent>
        </Card>
        <Card className="bg-red-500/5">
          <CardContent className="p-4">
            <p className="text-xs text-red-600">Bearish</p>
            <p className="text-2xl font-bold text-red-600">{bearishCount}</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-500/5">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Neutral</p>
            <p className="text-2xl font-bold">{neutralCount}</p>
          </CardContent>
        </Card>
      </div>

      <div className="flex gap-4 flex-wrap">
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="px-4 py-2 border rounded-lg bg-background"
        >
          <option value="all">All Directions</option>
          <option value="bullish">Bullish</option>
          <option value="bearish">Bearish</option>
          <option value="neutral">Neutral</option>
        </select>
        <select
          value={scanType}
          onChange={(e) => setScanType(e.target.value)}
          className="px-4 py-2 border rounded-lg bg-background"
        >
          <option value="all">All Types</option>
          {Object.entries(SCAN_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Scan Results ({filteredResults.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-8 text-center gap-3">
              <AlertCircle className="h-8 w-8 text-destructive" />
              <p className="text-muted-foreground">{error}</p>
              <Button variant="outline" onClick={runScan}>Retry</Button>
            </div>
          ) : filteredResults.length === 0 ? (
            <p className="text-center py-8 text-muted-foreground">No signals match your filters</p>
          ) : (
            <div className="space-y-3">
              {filteredResults.map((r) => (
                <div
                  key={r.id}
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50"
                >
                  <div className="flex items-center gap-4">
                    <div className="flex flex-col">
                      <span className="font-semibold">{r.symbol}</span>
                      <span className="text-xs text-muted-foreground">{r.name ?? '—'}</span>
                    </div>
                    <Badge variant="outline">{getScanTypeLabel(r.scan_type)}</Badge>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <p className="font-semibold">₹{formatINR(r.price)}</p>
                      <p className={`text-sm ${r.change_percent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {r.change_percent >= 0 ? '+' : ''}{r.change_percent.toFixed(2)}%
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-muted-foreground">Vol Ratio</p>
                      <p className="font-semibold">{r.volume_ratio != null ? `${r.volume_ratio.toFixed(1)}x` : 'N/A'}</p>
                    </div>
                    {r.details?.atr != null && (
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">ATR</p>
                        <p className="font-semibold">{r.details.atr.toFixed(2)}</p>
                      </div>
                    )}
                    <div className="text-right w-20">
                      <p className="text-xs text-muted-foreground">Confidence</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className={`h-full ${r.direction === 'bullish' ? 'bg-green-500' : r.direction === 'bearish' ? 'bg-red-500' : 'bg-gray-500'}`}
                            style={{ width: `${r.confidence}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium">{r.confidence}%</span>
                      </div>
                    </div>
                    {getDirectionBadge(r.direction)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
