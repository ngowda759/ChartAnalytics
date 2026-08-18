'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { optionsApi } from '@/lib/api';

interface OptionLeg {
  strike: number;
  oi: number;
  change_oi: number;
  volume: number;
  iv: number;
  ltp: number;
  bid: number;
  ask: number;
}

interface OptionChainResponse {
  symbol: string;
  expiry: string;
  spot_price: number;
  timestamp: string;
  calls: OptionLeg[];
  puts: OptionLeg[];
}

const SYMBOLS = [
  { value: 'NIFTY', label: 'NIFTY 50' },
  { value: 'BANKNIFTY', label: 'BANKNIFTY' },
  { value: 'FINNIFTY', label: 'FINNIFTY' },
];

export default function OptionsPage() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('NIFTY');
  const [chain, setChain] = useState<OptionChainResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async (symbol: string) => {
    setLoading(true);
    setError(null);
    const res = await optionsApi.getChain(symbol);
    if (res.error || !res.data) {
      setError(res.error ?? 'Option chain unavailable');
      setChain(null);
    } else {
      setChain(res.data as OptionChainResponse);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData(selectedSymbol);
  }, [selectedSymbol, fetchData]);

  const refreshData = () => fetchData(selectedSymbol);

  const calls = chain?.calls ?? [];
  const puts = chain?.puts ?? [];
  const totalCallOI = calls.reduce((acc, o) => acc + (o.oi || 0), 0);
  const totalPutOI = puts.reduce((acc, o) => acc + (o.oi || 0), 0);
  const pcr = totalCallOI > 0 ? totalPutOI / totalCallOI : 0;
  const spotPrice = chain?.spot_price ?? 0;

  const formatNumber = (num: number) => {
    if (num >= 10000000) return `${(num / 10000000).toFixed(2)} Cr`;
    if (num >= 100000) return `${(num / 100000).toFixed(2)} L`;
    return new Intl.NumberFormat('en-IN').format(num);
  };

  const formatINR = (num: number) =>
    new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num);

  // Merge calls + puts by strike for a single chain table.
  const strikes = Array.from(
    new Set([...calls.map((c) => c.strike), ...puts.map((p) => p.strike)])
  ).sort((a, b) => a - b);

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
            <p className="text-2xl font-bold">{spotPrice ? `₹${formatINR(spotPrice)}` : 'N/A'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">PCR</p>
            <p className={`text-2xl font-bold ${pcr > 1 ? 'text-green-600' : 'text-red-600'}`}>
              {totalCallOI > 0 ? pcr.toFixed(2) : 'N/A'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Total Call OI</p>
            <p className="text-2xl font-bold text-red-600">{totalCallOI ? formatNumber(totalCallOI) : 'N/A'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Total Put OI</p>
            <p className="text-2xl font-bold text-green-600">{totalPutOI ? formatNumber(totalPutOI) : 'N/A'}</p>
          </CardContent>
        </Card>
      </div>

      {chain && (
        <p className="text-xs text-muted-foreground">
          Expiry: {chain.expiry} • Updated: {new Date(chain.timestamp).toLocaleString('en-IN')}
        </p>
      )}

      {/* Options Table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Option Chain - {selectedSymbol}</CardTitle>
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
              <Button variant="outline" onClick={refreshData}>Retry</Button>
            </div>
          ) : strikes.length === 0 ? (
            <p className="text-center py-8 text-muted-foreground">No option chain data available</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-right py-2 px-2">Call OI</th>
                    <th className="text-right py-2 px-2">Call LTP</th>
                    <th className="text-center py-2 px-2">Strike</th>
                    <th className="text-right py-2 px-2">Put LTP</th>
                    <th className="text-right py-2 px-2">Put OI</th>
                  </tr>
                </thead>
                <tbody>
                  {strikes.map((strike) => {
                    const call = calls.find((c) => c.strike === strike);
                    const put = puts.find((p) => p.strike === strike);
                    return (
                      <tr key={strike} className="border-b hover:bg-muted/50">
                        <td className="text-right py-2 px-2 text-muted-foreground">{call ? formatNumber(call.oi) : '—'}</td>
                        <td className={`text-right py-2 px-2 ${call ? 'text-green-600 font-semibold' : 'text-muted-foreground'}`}>
                          {call ? `₹${call.ltp.toFixed(2)}` : '—'}
                        </td>
                        <td className="text-center py-2 px-2">
                          <Badge variant="outline" className="font-mono">₹{strike.toLocaleString('en-IN')}</Badge>
                        </td>
                        <td className={`text-right py-2 px-2 ${put ? 'text-red-600 font-semibold' : 'text-muted-foreground'}`}>
                          {put ? `₹${put.ltp.toFixed(2)}` : '—'}
                        </td>
                        <td className="text-right py-2 px-2 text-muted-foreground">{put ? formatNumber(put.oi) : '—'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
