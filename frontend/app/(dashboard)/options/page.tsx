'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, TrendingUp, TrendingDown } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface OptionContract {
  id: string;
  symbol: string;
  expiry: string;
  strike: number;
  type: 'CE' | 'PE';
  ltp: number;
  change: number;
  volume: number;
  oi: number;
  iv: number;
  delta: number;
  bid: number;
  ask: number;
}

const SYMBOLS = [
  { value: 'NIFTY', label: 'NIFTY 50', basePrice: 24500 },
  { value: 'BANKNIFTY', label: 'BANKNIFTY', basePrice: 52400 },
  { value: 'FINNIFTY', label: 'FINNIFTY', basePrice: 23400 },
];

function generateMockOptions(symbol: string, spotPrice: number): OptionContract[] {
  const contracts: OptionContract[] = [];
  const expiry = new Date();
  expiry.setDate(expiry.getDate() + (7 - expiry.getDay()) % 7 + (expiry.getDay() === 0 ? 1 : 0)); // Next Thursday
  const expiryStr = expiry.toISOString().split('T')[0];
  
  const strikes = [-300, -200, -100, -50, 0, 50, 100, 200, 300];
  
  strikes.forEach((offset, i) => {
    const strike = Math.round((spotPrice + offset) / 50) * 50;
    const isITM = (offset < 0 && i % 2 === 0) || (offset > 0 && i % 2 === 1);
    
    // CE prices
    const ceLtp = Math.max(0.5, Math.abs(spotPrice - strike) + (isITM ? -10 : 10) + Math.random() * 50);
    contracts.push({
      id: `${symbol}-CE-${strike}`,
      symbol,
      expiry: expiryStr,
      strike,
      type: 'CE',
      ltp: Math.round(ceLtp * 100) / 100,
      change: (Math.random() - 0.45) * 10,
      volume: Math.floor(Math.random() * 500000) + 100000,
      oi: Math.floor(Math.random() * 5000000) + 500000,
      iv: 15 + Math.random() * 10,
      delta: offset < 0 ? 0.7 + Math.random() * 0.25 : 0.15 + Math.random() * 0.25,
      bid: Math.round((ceLtp - 2) * 100) / 100,
      ask: Math.round((ceLtp + 2) * 100) / 100,
    });
    
    // PE prices
    const peLtp = Math.max(0.5, Math.abs(spotPrice - strike) + (isITM ? -10 : 10) + Math.random() * 50);
    contracts.push({
      id: `${symbol}-PE-${strike}`,
      symbol,
      expiry: expiryStr,
      strike,
      type: 'PE',
      ltp: Math.round(peLtp * 100) / 100,
      change: (Math.random() - 0.55) * 10,
      volume: Math.floor(Math.random() * 500000) + 100000,
      oi: Math.floor(Math.random() * 5000000) + 500000,
      iv: 15 + Math.random() * 10,
      delta: offset < 0 ? -0.7 - Math.random() * 0.25 : -0.15 - Math.random() * 0.25,
      bid: Math.round((peLtp - 2) * 100) / 100,
      ask: Math.round((peLtp + 2) * 100) / 100,
    });
  });
  
  return contracts.sort((a, b) => a.strike - b.strike);
}

export default function OptionsPage() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('NIFTY');
  const [options, setOptions] = useState<OptionContract[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [spotPrice, setSpotPrice] = useState(24500);

  useEffect(() => {
    const symbolConfig = SYMBOLS.find(s => s.value === selectedSymbol);
    if (symbolConfig) {
      setSpotPrice(symbolConfig.basePrice + (Math.random() - 0.5) * 200);
      setLoading(true);
      // Simulate API fetch
      setTimeout(() => {
        setOptions(generateMockOptions(selectedSymbol, symbolConfig.basePrice));
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
        setOptions(generateMockOptions(selectedSymbol, symbolConfig.basePrice));
        setLoading(false);
      }, 500);
    }
  };

  const filteredOptions = options.filter((opt) => {
    if (filter !== 'all' && opt.type !== filter) return false;
    return true;
  });

  const callContracts = filteredOptions.filter(o => o.type === 'CE');
  const putContracts = filteredOptions.filter(o => o.type === 'PE');
  const totalCallOI = callContracts.reduce((acc, o) => acc + o.oi, 0);
  const totalPutOI = putContracts.reduce((acc, o) => acc + o.oi, 0);
  const pcr = totalPutOI / totalCallOI;

  const formatNumber = (num: number) => {
    if (num >= 10000000) return `${(num / 10000000).toFixed(2)} Cr`;
    if (num >= 100000) return `${(num / 100000).toFixed(2)} L`;
    return new Intl.NumberFormat('en-IN').format(num);
  };

  const formatINR = (num: number) => {
    return new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Options Chain</h1>
          <p className="text-muted-foreground">Track and analyze options contracts</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={refreshData} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button size="sm">+ New Strategy</Button>
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

      {/* Spot Price & PCR */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Spot Price</p>
            <p className="text-2xl font-bold">₹{formatINR(spotPrice)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">PCR</p>
            <p className={`text-2xl font-bold ${pcr > 1 ? 'text-green-600' : 'text-red-600'}`}>
              {pcr.toFixed(2)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Total Call OI</p>
            <p className="text-2xl font-bold text-red-600">{formatNumber(totalCallOI)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Total Put OI</p>
            <p className="text-2xl font-bold text-green-600">{formatNumber(totalPutOI)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Filter */}
      <div className="flex gap-4">
        <Button
          variant={filter === 'all' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('all')}
        >
          All ({filteredOptions.length})
        </Button>
        <Button
          variant={filter === 'CE' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('CE')}
        >
          Calls ({callContracts.length})
        </Button>
        <Button
          variant={filter === 'PE' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('PE')}
        >
          Puts ({putContracts.length})
        </Button>
      </div>

      {/* Options Table - Mobile Friendly */}
      <Card className="overflow-hidden">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Option Chain - {selectedSymbol}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex justify-center py-8">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="overflow-x-auto -mx-4">
              <table className="w-full text-xs min-w-[800px]">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left py-2 px-3 font-medium">Strike</th>
                    <th className="text-right py-2 px-3 font-medium">OI</th>
                    <th className="text-right py-2 px-3 font-medium">Chg</th>
                    <th className="text-right py-2 px-3 font-medium hidden sm:table-cell">Vol</th>
                    <th className="text-right py-2 px-3 font-medium hidden md:table-cell">IV</th>
                    <th className="text-right py-2 px-3 font-medium hidden lg:table-cell">Delta</th>
                    <th className="text-right py-2 px-3 font-medium hidden lg:table-cell">Bid</th>
                    <th className="text-center py-2 px-3 font-medium">LTP</th>
                    <th className="text-left py-2 px-3 font-medium hidden lg:table-cell">Ask</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOptions.map((opt) => (
                    <tr key={opt.id} className="border-t hover:bg-muted/30">
                      <td className="py-2 px-3">
                        <Badge variant={opt.type === 'CE' ? 'outline' : 'secondary'} className="font-mono text-xs">
                          ₹{opt.strike.toLocaleString('en-IN')}
                        </Badge>
                      </td>
                      <td className="text-right py-2 px-3">{formatNumber(opt.oi)}</td>
                      <td className={`text-right py-2 px-3 ${opt.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {opt.change >= 0 ? '+' : ''}{opt.change.toFixed(1)}%
                      </td>
                      <td className="text-right py-2 px-3 hidden sm:table-cell">{formatNumber(opt.volume)}</td>
                      <td className="text-right py-2 px-3 hidden md:table-cell">{opt.iv.toFixed(1)}%</td>
                      <td className={`text-right py-2 px-3 hidden lg:table-cell ${opt.delta > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {opt.delta.toFixed(2)}
                      </td>
                      <td className="text-right py-2 px-3 text-muted-foreground hidden lg:table-cell">₹{opt.bid.toFixed(2)}</td>
                      <td className={`text-center py-2 px-3 font-semibold ${opt.type === 'CE' ? 'text-green-600' : 'text-red-600'}`}>
                        ₹{opt.ltp.toFixed(2)}
                      </td>
                      <td className="text-left py-2 px-3 text-muted-foreground hidden lg:table-cell">₹{opt.ask.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
