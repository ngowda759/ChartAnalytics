'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, TrendingUp, TrendingDown, Activity, BarChart3 } from 'lucide-react';

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
  { value: 'NIFTY', label: 'NIFTY 50', basePrice: 24500 },
  { value: 'BANKNIFTY', label: 'BANKNIFTY', basePrice: 52400 },
  { value: 'FINNIFTY', label: 'FINNIFTY', basePrice: 23400 },
];

function calculateIndicators(spotPrice: number): IndicatorValue[] {
  const volatility = 0.02;
  
  // Simulate calculated indicator values
  const rsi = 45 + Math.random() * 30; // 45-75 range
  const macd = (Math.random() - 0.4) * 100;
  const macdSignal = (Math.random() - 0.4) * 80;
  const macdHistogram = macd - macdSignal;
  
  const ema20 = spotPrice * (1 + (Math.random() - 0.5) * 0.02);
  const ema50 = spotPrice * (1 + (Math.random() - 0.5) * 0.03);
  const sma20 = spotPrice * (1 + (Math.random() - 0.5) * 0.02);
  
  const bbUpper = spotPrice * 1.03;
  const bbMiddle = spotPrice;
  const bbLower = spotPrice * 0.97;
  
  const atr = spotPrice * volatility * 0.1;
  const adx = 20 + Math.random() * 40;
  
  const stochasticK = Math.random() * 100;
  const stochasticD = Math.random() * 100;
  
  const vwap = spotPrice * (1 + (Math.random() - 0.5) * 0.005);
  const obv = Math.random() > 0.5 ? 1 : -1;
  
  const supertrend = Math.random() > 0.5 ? spotPrice * 0.995 : spotPrice * 1.005;
  const stDirection = supertrend < spotPrice ? 'bullish' : 'bearish';
  
  return [
    {
      id: 'rsi',
      name: 'Relative Strength Index',
      shortName: 'RSI',
      value: rsi,
      signal: rsi > 70 ? 'bearish' : rsi < 30 ? 'bullish' : 'neutral',
      description: 'Overbought (>70) / Oversold (<30)',
      unit: '',
    },
    {
      id: 'macd',
      name: 'MACD',
      shortName: 'MACD',
      value: macd,
      signal: macdHistogram > 0 ? 'bullish' : 'bearish',
      description: `${macd > macdSignal ? 'MACD above Signal' : 'MACD below Signal'} | Histogram: ${macdHistogram.toFixed(2)}`,
      unit: '',
    },
    {
      id: 'ema20',
      name: 'EMA 20',
      shortName: 'EMA 20',
      value: ema20,
      signal: ema20 > spotPrice ? 'bullish' : 'bearish',
      description: `EMA: ₹${ema20.toFixed(2)} | Price: ₹${spotPrice.toFixed(2)}`,
      unit: '',
    },
    {
      id: 'ema50',
      name: 'EMA 50',
      shortName: 'EMA 50',
      value: ema50,
      signal: ema50 > spotPrice ? 'bullish' : 'bearish',
      description: `EMA: ₹${ema50.toFixed(2)} | Price: ₹${spotPrice.toFixed(2)}`,
      unit: '',
    },
    {
      id: 'sma20',
      name: 'SMA 20',
      shortName: 'SMA 20',
      value: sma20,
      signal: sma20 > spotPrice ? 'bullish' : 'bearish',
      description: `SMA: ₹${sma20.toFixed(2)} | Price: ₹${spotPrice.toFixed(2)}`,
      unit: '',
    },
    {
      id: 'bb',
      name: 'Bollinger Bands',
      shortName: 'BB',
      value: ((spotPrice - bbLower) / (bbUpper - bbLower)) * 100,
      signal: spotPrice > bbUpper ? 'bearish' : spotPrice < bbLower ? 'bullish' : 'neutral',
      description: `Upper: ₹${bbUpper.toFixed(2)} | Middle: ₹${bbMiddle.toFixed(2)} | Lower: ₹${bbLower.toFixed(2)}`,
      unit: '%',
    },
    {
      id: 'atr',
      name: 'Average True Range',
      shortName: 'ATR',
      value: atr,
      signal: atr > spotPrice * 0.02 ? 'bearish' : 'neutral',
      description: 'High volatility indicator',
      unit: '₹',
    },
    {
      id: 'adx',
      name: 'Average Directional Index',
      shortName: 'ADX',
      value: adx,
      signal: adx > 25 ? 'bullish' : 'neutral',
      description: `${adx > 25 ? 'Strong trend' : 'Weak trend'}`,
      unit: '',
    },
    {
      id: 'stochastic',
      name: 'Stochastic',
      shortName: 'STOCH',
      value: stochasticK,
      signal: stochasticK > 80 ? 'bearish' : stochasticK < 20 ? 'bullish' : 'neutral',
      description: `K: ${stochasticK.toFixed(1)} | D: ${stochasticD.toFixed(1)}`,
      unit: '',
    },
    {
      id: 'vwap',
      name: 'VWAP',
      shortName: 'VWAP',
      value: vwap,
      signal: vwap > spotPrice ? 'bullish' : 'bearish',
      description: `VWAP: ₹${vwap.toFixed(2)} | Price: ₹${spotPrice.toFixed(2)}`,
      unit: '',
    },
    {
      id: 'supertrend',
      name: 'Supertrend',
      shortName: 'ST',
      value: supertrend,
      signal: stDirection,
      description: `${stDirection === 'bullish' ? 'Above price' : 'Below price'} | Level: ₹${supertrend.toFixed(2)}`,
      unit: '',
    },
  ];
}

export default function IndicatorsPage() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('NIFTY');
  const [indicators, setIndicators] = useState<IndicatorValue[]>([]);
  const [loading, setLoading] = useState(true);
  const [spotPrice, setSpotPrice] = useState(24500);

  useEffect(() => {
    const symbolConfig = SYMBOLS.find(s => s.value === selectedSymbol);
    if (symbolConfig) {
      setSpotPrice(symbolConfig.basePrice + (Math.random() - 0.5) * 200);
      setLoading(true);
      setTimeout(() => {
        setIndicators(calculateIndicators(symbolConfig.basePrice));
        setLoading(false);
      }, 500);
    }
  }, [selectedSymbol]);

  const refreshData = () => {
    const symbolConfig = SYMBOLS.find(s => s.value === selectedSymbol);
    if (symbolConfig) {
      setLoading(true);
      setTimeout(() => {
        setSpotPrice(symbolConfig.basePrice + (Math.random() - 0.5) * 200);
        setIndicators(calculateIndicators(symbolConfig.basePrice));
        setLoading(false);
      }, 500);
    }
  };

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
            <p className="text-2xl font-bold">₹{spotPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
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
                <div className="bg-green-500" style={{ width: `${(bullishCount / indicators.length) * 100}%` }} />
                <div className="bg-gray-400" style={{ width: `${(neutralCount / indicators.length) * 100}%` }} />
                <div className="bg-red-500" style={{ width: `${(bearishCount / indicators.length) * 100}%` }} />
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
                {bullishCount > bearishCount ? 'BULLISH' : 
                 bearishCount > bullishCount ? 'BEARISH' : 'NEUTRAL'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
