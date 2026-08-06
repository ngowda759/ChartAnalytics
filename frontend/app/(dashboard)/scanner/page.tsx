'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, TrendingUp, TrendingDown, Zap, Activity } from 'lucide-react';

interface ScanResult {
  id: string;
  symbol: string;
  name: string;
  scan_type: 'breakout' | 'ema_cross' | 'volume_spike' | 'rsi_extreme' | 'ma_cross';
  direction: 'bullish' | 'bearish' | 'neutral';
  confidence: number;
  price: number;
  change_percent: number;
  volume_ratio: number;
  signal_strength: number;
  timestamp: string;
}

const STOCKS = [
  { symbol: 'RELIANCE', name: 'Reliance Industries', basePrice: 2980 },
  { symbol: 'HDFCBANK', name: 'HDFC Bank', basePrice: 1695 },
  { symbol: 'ICICIBANK', name: 'ICICI Bank', basePrice: 1120 },
  { symbol: 'TCS', name: 'Tata Consultancy', basePrice: 4150 },
  { symbol: 'INFY', name: 'Infosys', basePrice: 1850 },
  { symbol: 'ITC', name: 'ITC Limited', basePrice: 485 },
  { symbol: 'LT', name: 'Larsen & Toubro', basePrice: 3650 },
  { symbol: 'SBIN', name: 'State Bank of India', basePrice: 820 },
  { symbol: 'BHARTIARTL', name: 'Bharti Airtel', basePrice: 1580 },
  { symbol: 'ADANIPORTS', name: 'Adani Ports', basePrice: 1420 },
  { symbol: 'TATASTEEL', name: 'Tata Steel', basePrice: 185 },
  { symbol: 'NESTLEIND', name: 'Nestle India', basePrice: 2450 },
  { symbol: 'MARUTI', name: 'Maruti Suzuki', basePrice: 12800 },
  { symbol: 'BAJFINANCE', name: 'Bajaj Finance', basePrice: 7850 },
  { symbol: 'KOTAKBANK', name: 'Kotak Bank', basePrice: 1780 },
];

const SCAN_TYPES = [
  { value: 'breakout', label: 'Breakout', icon: Zap },
  { value: 'ema_cross', label: 'EMA Cross', icon: TrendingUp },
  { value: 'volume_spike', label: 'Volume Spike', icon: Activity },
  { value: 'rsi_extreme', label: 'RSI Extreme', icon: Activity },
  { value: 'ma_cross', label: 'MA Cross', icon: TrendingUp },
];

function generateScanResults(): ScanResult[] {
  const results: ScanResult[] = [];
  const selectedStocks = STOCKS.sort(() => Math.random() - 0.5).slice(0, 8);
  
  selectedStocks.forEach((stock, i) => {
    const scanTypes: ScanResult['scan_type'][] = ['breakout', 'ema_cross', 'volume_spike', 'rsi_extreme', 'ma_cross'];
    const directions: ScanResult['direction'][] = ['bullish', 'bearish', 'neutral'];
    const directions_weights = [0.5, 0.3, 0.2]; // 50% bullish, 30% bearish, 20% neutral
    
    const rand = Math.random();
    let direction: ScanResult['direction'] = 'neutral';
    if (rand < directions_weights[0]) direction = 'bullish';
    else if (rand < directions_weights[0] + directions_weights[1]) direction = 'bearish';
    
    const scanType = scanTypes[Math.floor(Math.random() * scanTypes.length)];
    const priceVariation = (Math.random() - 0.5) * 0.05;
    const price = stock.basePrice * (1 + priceVariation);
    
    results.push({
      id: `scan-${i}`,
      symbol: stock.symbol,
      name: stock.name,
      scan_type: scanType,
      direction,
      confidence: Math.floor(Math.random() * 30) + 65,
      price,
      change_percent: (Math.random() - 0.4) * 8,
      volume_ratio: Math.random() * 2 + 1.2,
      signal_strength: Math.floor(Math.random() * 40) + 60,
      timestamp: new Date().toISOString(),
    });
  });
  
  return results.sort((a, b) => b.confidence - a.confidence);
}

export default function ScannerPage() {
  const [results, setResults] = useState<ScanResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [scanType, setScanType] = useState<string>('all');
  const [lastScan, setLastScan] = useState<Date | null>(null);

  const runScan = () => {
    setLoading(true);
    setTimeout(() => {
      setResults(generateScanResults());
      setLastScan(new Date());
      setLoading(false);
    }, 800);
  };

  useEffect(() => {
    runScan();
  }, []);

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

  const getScanTypeLabel = (type: ScanResult['scan_type']) => {
    return SCAN_TYPES.find(t => t.value === type)?.label || type;
  };

  const formatINR = (num: number) => {
    return new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Market Scanner</h1>
          <p className="text-muted-foreground">
            Find trading opportunities in real-time
            {lastScan && (
              <span className="ml-2 text-xs">
                • Last scan: {lastScan.toLocaleTimeString('en-IN')}
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
          {SCAN_TYPES.map((type) => (
            <option key={type.value} value={type.value}>{type.label}</option>
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
                      <span className="text-xs text-muted-foreground">{r.name}</span>
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
                      <p className="font-semibold">{r.volume_ratio.toFixed(1)}x</p>
                    </div>
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
