'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Plus, Play, Pause, TrendingUp, TrendingDown } from 'lucide-react';

interface Strategy {
  id: string;
  name: string;
  type: string;
  description: string;
  is_active: boolean;
  metrics: {
    winRate: number;
    profitFactor: number;
    totalTrades: number;
    avgProfit: number;
    avgLoss: number;
  };
}

const strategyTypes = [
  { value: 'EMA_CROSSOVER', label: 'EMA Crossover', description: 'Trade when fast EMA crosses slow EMA', color: 'blue' },
  { value: 'RSI', label: 'RSI Reversal', description: 'Trade RSI overbought/oversold reversals', color: 'purple' },
  { value: 'VWAP', label: 'VWAP', description: 'Trade VWAP breakouts and bounces', color: 'green' },
  { value: 'MOMENTUM', label: 'Momentum', description: 'Trade with momentum indicators', color: 'orange' },
  { value: 'BREAKOUT', label: 'Breakout', description: 'Trade price breakouts from ranges', color: 'red' },
  { value: 'ORB', label: 'Opening Range', description: 'Opening range breakout strategy', color: 'cyan' },
];

const mockStrategies: Strategy[] = [
  { id: '1', name: 'EMA Crossover NIFTY', type: 'EMA_CROSSOVER', description: 'Trade EMA 20/50 crossovers on NIFTY for momentum entries', is_active: true, metrics: { winRate: 62, profitFactor: 1.8, totalTrades: 45, avgProfit: 2500, avgLoss: -1200 } },
  { id: '2', name: 'RSI Reversal', type: 'RSI', description: 'RSI overbought/oversold reversals on BankNifty', is_active: true, metrics: { winRate: 55, profitFactor: 1.5, totalTrades: 32, avgProfit: 1800, avgLoss: -900 } },
  { id: '3', name: 'VWAP Breakout', type: 'VWAP', description: 'VWAP support/resistance bounces with tight SL', is_active: false, metrics: { winRate: 58, profitFactor: 1.6, totalTrades: 28, avgProfit: 3200, avgLoss: -1500 } },
  { id: '4', name: 'Supertrend Momentum', type: 'MOMENTUM', description: 'Supertrend + RSI confirmation for trend trades', is_active: true, metrics: { winRate: 68, profitFactor: 2.1, totalTrades: 38, avgProfit: 4100, avgLoss: -1800 } },
];

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>(mockStrategies);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedType, setSelectedType] = useState('EMA_CROSSOVER');
  const [newStrategyName, setNewStrategyName] = useState('');

  const toggleStrategy = (id: string) => {
    setStrategies(strategies.map(s => 
      s.id === id ? { ...s, is_active: !s.is_active } : s
    ));
  };

  const formatINR = (num: number) => {
    const formatted = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(Math.abs(num));
    return num >= 0 ? `+₹${formatted}` : `-₹${formatted}`;
  };

  const getTypeColor = (type: string) => {
    return strategyTypes.find(t => t.value === type)?.color || 'gray';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Strategy Builder</h1>
          <p className="text-muted-foreground">Create and manage your trading strategies</p>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : '+ Create Strategy'}
        </Button>
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
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {strategies.map((strategy) => (
          <Card key={strategy.id} className={strategy.is_active ? 'border-green-500/50' : ''}>
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between">
                <div className="flex flex-col gap-1">
                  <CardTitle className="text-base sm:text-lg">{strategy.name}</CardTitle>
                  <div className="flex items-center gap-2">
                    <Badge variant={strategy.is_active ? 'default' : 'secondary'} className={`text-xs ${strategy.is_active ? 'bg-green-500' : ''}`}>
                      {strategy.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                    <Badge variant="outline" className="text-xs hidden sm:inline-flex">
                      {strategyTypes.find(t => t.value === strategy.type)?.label}
                    </Badge>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => toggleStrategy(strategy.id)}
                >
                  {strategy.is_active ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4 line-clamp-2">{strategy.description}</p>
              
              <div className="grid grid-cols-3 gap-2 sm:gap-4 mb-4">
                <div className="text-center p-2 sm:p-3 bg-green-500/10 rounded-lg">
                  <p className="text-xs text-muted-foreground mb-1">Win Rate</p>
                  <p className="text-lg sm:text-xl font-bold text-green-600">{strategy.metrics.winRate}%</p>
                </div>
                <div className="text-center p-2 sm:p-3 bg-blue-500/10 rounded-lg">
                  <p className="text-xs text-muted-foreground mb-1">PF</p>
                  <p className="text-lg sm:text-xl font-bold text-blue-600">{strategy.metrics.profitFactor.toFixed(1)}</p>
                </div>
                <div className="text-center p-2 sm:p-3 bg-muted rounded-lg">
                  <p className="text-xs text-muted-foreground mb-1">Trades</p>
                  <p className="text-lg sm:text-xl font-bold">{strategy.metrics.totalTrades}</p>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-sm border-t pt-4">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1">
                    <TrendingUp className="h-4 w-4 text-green-600" />
                    <span className="text-green-600 text-xs sm:text-sm">{formatINR(strategy.metrics.avgProfit)}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <TrendingDown className="h-4 w-4 text-red-600" />
                    <span className="text-red-600 text-xs sm:text-sm">{formatINR(strategy.metrics.avgLoss)}</span>
                  </div>
                </div>
                <div className="flex gap-2 w-full sm:w-auto">
                  <Button variant="outline" size="sm" className="flex-1 sm:flex-none">Edit</Button>
                  <Button variant="outline" size="sm" className="flex-1 sm:flex-none">Backtest</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

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
