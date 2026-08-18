'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, TrendingUp, TrendingDown, Activity, BarChart3 } from 'lucide-react';
import { indicatorsApi } from '@/lib/api';

interface IndicatorValue {
  id: string;
  name: string;
  shortName: string;
  value: number;
  signal: 'bullish' | 'bearish' | 'neutral';
  description: string;
  unit: string;
}

const SYMBOLS = [
  { value: 'NIFTY', label: 'NIFTY 50' },
  { value: 'BANKNIFTY', label: 'BANKNIFTY' },
  { value: 'FINNIFTY', label: 'FINNIFTY' },
];

function mapIndicators(data: any, spotPrice: number): IndicatorValue[] {
  if (!data) return [];
  const ema = data.ema || {};
  const rsi = data.rsi || {};
  const macd = data.macd || {};
  const vwap = data.vwap || {};
  const supertrend = data.supertrend || {};
  const bb = data.bollinger_bands || {};
  const atr = data.atr || {};
  const adx = data.adx || {};

  const rsiSignal =
    rsi.signal === 'overbought'
      ? 'bearish'
      : rsi.signal === 'oversold'
        ? 'bullish'
        : 'neutral';
  const macdSignal =
    macd.histogram > 0 ? 'bullish' : macd.histogram < 0 ? 'bearish' : 'neutral';
  const emaTrend =
    ema.trend === 'bullish' ? 'bullish' : ema.trend === 'bearish' ? 'bearish' : 'neutral';
  const stSignal = supertrend.direction === 'up' ? 'bullish' : 'bearish';

  return [
    {
      id: 'rsi',
      name: 'Relative Strength Index',
      shortName: 'RSI',
      value: rsi.value ?? 0,
      signal: rsiSignal,
      description: rsi.signal ? `Signal: ${rsi.signal}` : '',
      unit: '',
    },
    {
      id: 'macd',
      name: 'MACD',
      shortName: 'MACD',
      value: macd.macd ?? 0,
      signal: macdSignal,
      description: `Histogram: ${(macd.histogram ?? 0).toFixed(2)} | Crossover: ${macd.crossover ?? 'none'}`,
      unit: '',
    },
    {
      id: 'ema',
      name: 'Exponential Moving Avg',
      shortName: 'EMA',
      value: ema.ema_20 ?? 0,
      signal: emaTrend,
      description: `EMA20: ${(ema.ema_20 ?? 0).toFixed(2)} | EMA50: ${(ema.ema_50 ?? 0).toFixed(2)}`,
      unit: '',
    },
    {
      id: 'bollinger',
      name: 'Bollinger Bands',
      shortName: 'BB',
      value: bb.middle ?? spotPrice,
      signal: (bb.position ?? 50) > 80 ? 'bearish' : (bb.position ?? 50) < 20 ? 'bullish' : 'neutral',
      description: `Upper: ${(bb.upper ?? 0).toFixed(2)} | Lower: ${(bb.lower ?? 0).toFixed(2)}`,
      unit: '',
    },
    {
      id: 'atr',
      name: 'Average True Range',
      shortName: 'ATR',
      value: atr.value ?? 0,
      signal: 'neutral',
      description: `Volatility: ${atr.signal ?? 'medium'} | ${(atr.percent ?? 0).toFixed(2)}%`,
      unit: '',
    },
    {
      id: 'adx',
      name: 'ADX (Trend Strength)',
      shortName: 'ADX',
      value: adx.value ?? 0,
      signal: (adx.plus_di ?? 0) > (adx.minus_di ?? 0) ? 'bullish' : 'bearish',
      description: `Strength: ${adx.trend_strength ?? 'weak'}`,
      unit: '',
    },
    {
      id: 'vwap',
      name: 'VWAP',
      shortName: 'VWAP',
      value: vwap.value ?? 0,
      signal: (vwap.value ?? 0) > spotPrice ? 'bullish' : 'bearish',
      description: vwap.signal ? `${vwap.signal} VWAP` : '',
      unit: '',
    },
    {
      id: 'supertrend',
      name: 'Supertrend',
      shortName: 'ST',
      value: supertrend.value ?? 0,
      signal: stSignal,
      description: `Direction: ${supertrend.direction ?? '—'} | Breakout: ${supertrend.is_breakout ? 'Yes' : 'No'}`,
      unit: '',
    },
  ];
}

export default function IndicatorsPage() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('NIFTY');
  const [indicators, setIndicators] = useState<IndicatorValue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [spotPrice, setSpotPrice] = useState<number | null>(null);

  const loadIndicators = useCallback(async (symbol: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await indicatorsApi.getIndicators(symbol);
      const payload = result?.data ?? null;
      const price = payload?.price ?? null;
      setSpotPrice(price);
      setIndicators(mapIndicators(payload, price ?? 0));
    } catch (e: any) {
      setError(
        e?.message?.includes('404')
          ? 'Insufficient historical data to compute indicators for this symbol.'
          : 'Indicators unavailable. Live market data could not be loaded.'
      );
      setIndicators([]);
      setSpotPrice(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadIndicators(selectedSymbol);
  }, [selectedSymbol, loadIndicators]);

  const refreshData = () => loadIndicators(selectedSymbol);

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'bullish': return 'text-green-600 bg-green-500/10 border-green-500';
      case 'bearish': return 'text-red-600 bg-red-500/10 border-red-500';
      default: return 'text-gray-600 bg-gray-500/10 border-gray-500';
    }
  };

  const getSignalIcon = (signal: string) => {
    if (signal === 'bullish') return <TrendingUp className="h-4 w-4" />;
    if (signal === 'bearish') return <TrendingDown className="h-4 w-4" />;
    return <Activity className="h-4 w-4" />;
  };

  const bullishCount = indicators.filter(i => i.signal === 'bullish').length;
  const bearishCount = indicators.filter(i => i.signal === 'bearish').length;
  const neutralCount = indicators.filter(i => i.signal === 'neutral').length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Technical Indicators</h1>
          <p className="text-muted-foreground">Live indicator values and signals</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={refreshData} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button size="sm">+ Add Indicator</Button>
        </div>
      </div>

      {/* Symbol Selection */}
      <div className="flex gap-2">
        {SYMBOLS.map((sym) => (
          <Button
            key={sym.value}
            variant={selectedSymbol === sym.value ? 'default' : 'outline'}
            onClick={() => setSelectedSymbol(sym.value)}
          >
            {sym.label}
          </Button>
        ))}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Spot Price</p>
            <p className="text-2xl font-bold">
              {spotPrice != null
                ? `₹${spotPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                : 'N/A'}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-green-500/5">
          <CardContent className="p-4">
            <p className="text-xs text-green-600 flex items-center gap-1">
              <TrendingUp className="h-3 w-3" /> Bullish
            </p>
            <p className="text-2xl font-bold text-green-600">{bullishCount}</p>
          </CardContent>
        </Card>
        <Card className="bg-red-500/5">
          <CardContent className="p-4">
            <p className="text-xs text-red-600 flex items-center gap-1">
              <TrendingDown className="h-3 w-3" /> Bearish
            </p>
            <p className="text-2xl font-bold text-red-600">{bearishCount}</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-500/5">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <Activity className="h-3 w-3" /> Neutral
            </p>
            <p className="text-2xl font-bold">{neutralCount}</p>
          </CardContent>
        </Card>
      </div>

      {/* Indicators Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {loading ? (
          Array(8).fill(0).map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-4">
                <div className="h-4 bg-muted rounded w-1/2 mb-2"></div>
                <div className="h-8 bg-muted rounded w-3/4"></div>
              </CardContent>
            </Card>
          ))
        ) : error ? (
          <Card className="col-span-full">
            <CardContent className="p-6 text-center text-muted-foreground">
              {error}
            </CardContent>
          </Card>
        ) : (
          indicators.map((ind) => (
            <Card key={ind.id} className={`border-l-4 ${getSignalColor(ind.signal)}`}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium">{ind.name}</CardTitle>
                  <Badge variant="outline" className="flex items-center gap-1">
                    {getSignalIcon(ind.signal)}
                    {ind.signal}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-end justify-between">
                  <div>
                    <p className="text-2xl font-bold">
                      {ind.unit === '₹' ? '₹' : ''}
                      {ind.value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      {ind.unit === '%' ? '%' : ''}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">{ind.description}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Combined Signal */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Overall Market Signal
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="flex h-4 rounded-full overflow-hidden bg-muted">
                <div className="bg-green-500" style={{ width: `${indicators.length ? (bullishCount / indicators.length) * 100 : 0}%` }} />
                <div className="bg-gray-400" style={{ width: `${indicators.length ? (neutralCount / indicators.length) * 100 : 0}%` }} />
                <div className="bg-red-500" style={{ width: `${indicators.length ? (bearishCount / indicators.length) * 100 : 0}%` }} />
              </div>
              <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                <span>Bullish: {bullishCount}</span>
                <span>Neutral: {neutralCount}</span>
                <span>Bearish: {bearishCount}</span>
              </div>
            </div>
            <div className="text-center px-4">
              <p className="text-xs text-muted-foreground">Signal</p>
              <p className={`text-xl font-bold ${
                bullishCount > bearishCount ? 'text-green-600' : 
                bearishCount > bullishCount ? 'text-red-600' : 'text-gray-600'
              }`}>
                {!indicators.length
                  ? 'N/A'
                  : bullishCount > bearishCount ? 'BULLISH' : 
                   bearishCount > bullishCount ? 'BEARISH' : 'NEUTRAL'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
