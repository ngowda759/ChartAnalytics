'use client';

import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Plus, Play, Pause, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';
import { strategiesApi } from '@/lib/api';

interface StrategyMetrics {
  winRate: number | null;
  profitFactor: number | null;
  totalTrades: number | null;
  avgProfit: number | null;
  avgLoss: number | null;
}

interface Strategy {
  id: string;
  name: string;
  type: string;
  description: string;
  is_active: boolean;
  metrics: StrategyMetrics;
}

const strategyTypes = [
  { value: 'EMA_CROSSOVER', label: 'EMA Crossover', description: 'Trade when fast EMA crosses slow EMA', color: 'blue' },
  { value: 'RSI', label: 'RSI Reversal', description: 'Trade RSI overbought/oversold reversals', color: 'purple' },
  { value: 'VWAP', label: 'VWAP', description: 'Trade VWAP breakouts and bounces', color: 'green' },
  { value: 'MOMENTUM', label: 'Momentum', description: 'Trade with momentum indicators', color: 'orange' },
  { value: 'BREAKOUT', label: 'Breakout', description: 'Trade price breakouts from ranges', color: 'red' },
  { value: 'ORB', label: 'Opening Range', description: 'Opening range breakout strategy', color: 'cyan' },
];

// Backend Strategy has no performance metrics; surface N/A rather than
// fabricate win rate / profit factor.
const NO_METRICS: StrategyMetrics = {
  winRate: null,
  profitFactor: null,
  totalTrades: null,
  avgProfit: null,
  avgLoss: null,
};

function toStrategy(raw: Record<string, unknown>): Strategy {
  return {
    id: String(raw.id ?? ''),
    name: String(raw.name ?? 'Untitled'),
    type: String(raw.type ?? 'CUSTOM'),
    description: String(raw.description ?? ''),
    is_active: Boolean(raw.is_active),
    metrics: NO_METRICS,
  };
}

export default function StrategiesPage() {
  const [localOverrides, setLocalOverrides] = useState<Record<string, boolean>>({});
  const [showCreate, setShowCreate] = useState(false);
  const [selectedType, setSelectedType] = useState('EMA_CROSSOVER');
  const [newStrategyName, setNewStrategyName] = useState('');

  const fetchStrategies = useCallback(async (): Promise<Strategy[]> => {
    const { data, error } = await strategiesApi.getStrategies();
    if (error || !data) {
      throw new Error(error || 'Failed to load strategies');
    }
    return (data as unknown[]).map((s) =>
      toStrategy(s as Record<string, unknown>)
    );
  }, []);

  const { data: strategies, isLoading, isError, refetch, isFetching } =
    useQuery<Strategy[]>({
      queryKey: ['strategies'],
      queryFn: fetchStrategies,
      refetchOnWindowFocus: false,
    });

  // Apply local toggle overrides (preserve existing in-memory toggle UX).
  const displayed = (strategies ?? []).map((s) =>
    localOverrides[s.id] !== undefined
      ? { ...s, is_active: localOverrides[s.id] }
      : s
  );

  const toggleStrategy = (id: string) => {
    const current = displayed.find((s) => s.id === id);
    if (!current) return;
    setLocalOverrides((prev) => ({ ...prev, [id]: !current.is_active }));
  };

  const formatINR = (num: number | null) => {
    if (num === null) return 'N/A';
    const formatted = new Intl.NumberFormat('en-IN', {
      maximumFractionDigits: 0,
    }).format(Math.abs(num));
    return num >= 0 ? `+₹${formatted}` : `-₹${formatted}`;
  };

  const getTypeColor = (type: string) => {
    return strategyTypes.find((t) => t.value === type)?.color || 'gray';
  };

  const fmtMetric = (v: number | null, digits = 0, suffix = '') =>
    v === null ? 'N/A' : `${v.toFixed(digits)}${suffix}`;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Strategy Builder</h1>
          <p className="text-muted-foreground">Create and manage your trading strategies</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button onClick={() => setShowCreate(!showCreate)}>
            {showCreate ? 'Cancel' : '+ Create Strategy'}
          </Button>
        </div>
      </div>

      {showCreate && (
        <Card>
          <CardHeader>
            <CardTitle>Create New Strategy</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Strategy Name</label>
                <input 
                  type="text" 
                  placeholder="My Strategy"
                  value={newStrategyName}
                  onChange={(e) => setNewStrategyName(e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg bg-background" 
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Strategy Type</label>
                <select 
                  value={selectedType} 
                  onChange={(e) => setSelectedType(e.target.value)} 
                  className="w-full px-4 py-2 border rounded-lg bg-background"
                >
                  {strategyTypes.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <h3 className="font-medium mb-2">{strategyTypes.find(t => t.value === selectedType)?.label}</h3>
              <p className="text-sm text-muted-foreground">{strategyTypes.find(t => t.value === selectedType)?.description}</p>
            </div>
            <Button className="w-full md:w-auto">Create Strategy</Button>
          </CardContent>
        </Card>
      )}

      {/* Strategy Cards */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="h-64 animate-pulse bg-muted/40" />
          ))}
        </div>
      ) : isError ? (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            Unable to load strategies. Click Refresh to retry.
          </CardContent>
        </Card>
      ) : displayed.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            No strategies yet. Create one to get started.
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {displayed.map((strategy) => (
            <Card key={strategy.id} className={strategy.is_active ? 'border-green-500/50' : ''}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-lg">{strategy.name}</CardTitle>
                    <Badge variant={strategy.is_active ? 'default' : 'secondary'} className={strategy.is_active ? 'bg-green-500' : ''}>
                      {strategy.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => toggleStrategy(strategy.id)}
                  >
                    {strategy.is_active ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  </Button>
                </div>
                <Badge variant="outline" className={`w-fit bg-${getTypeColor(strategy.type)}-500/10`}>
                  {strategyTypes.find(t => t.value === strategy.type)?.label ?? strategy.type}
                </Badge>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">{strategy.description || 'No description'}</p>

                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="text-center p-3 bg-green-500/10 rounded-lg">
                    <p className="text-xs text-muted-foreground mb-1">Win Rate</p>
                    <p className="text-xl font-bold text-green-600">{fmtMetric(strategy.metrics.winRate, 0, '%')}</p>
                  </div>
                  <div className="text-center p-3 bg-blue-500/10 rounded-lg">
                    <p className="text-xs text-muted-foreground mb-1">Profit Factor</p>
                    <p className="text-xl font-bold text-blue-600">{fmtMetric(strategy.metrics.profitFactor, 1)}</p>
                  </div>
                  <div className="text-center p-3 bg-muted rounded-lg">
                    <p className="text-xs text-muted-foreground mb-1">Total Trades</p>
                    <p className="text-xl font-bold">{fmtMetric(strategy.metrics.totalTrades)}</p>
                  </div>
                </div>

                <div className="flex items-center justify-between text-sm border-t pt-4">
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1">
                      <TrendingUp className="h-4 w-4 text-green-600" />
                      <span className="text-green-600">{formatINR(strategy.metrics.avgProfit)}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <TrendingDown className="h-4 w-4 text-red-600" />
                      <span className="text-red-600">{formatINR(strategy.metrics.avgLoss)}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">Edit</Button>
                    <Button variant="outline" size="sm">Backtest</Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Strategy Types Guide */}
      <Card>
        <CardHeader>
          <CardTitle>Strategy Types Guide</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {strategyTypes.map((type) => (
              <div key={type.value} className="border rounded-lg p-4">
                <h3 className="font-medium flex items-center gap-2">
                  <span className={`w-3 h-3 rounded-full bg-${type.color}-500`} />
                  {type.label}
                </h3>
                <p className="text-sm text-muted-foreground mt-1">{type.description}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
