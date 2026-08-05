'use client';

import { useState } from 'react';

interface Strategy {
  id: string;
  name: string;
  type: string;
  description: string;
  is_active: boolean;
  metrics?: {
    winRate: number;
    profitFactor: number;
    totalTrades: number;
  };
}

const mockStrategies: Strategy[] = [
  { id: '1', name: 'EMA Crossover NIFTY', type: 'EMA_CROSSOVER', description: 'Trade EMA 20/50 crossovers', is_active: true, metrics: { winRate: 62, profitFactor: 1.8, totalTrades: 45 } },
  { id: '2', name: 'RSI Reversal', type: 'RSI', description: 'RSI overbought/oversold reversals', is_active: true, metrics: { winRate: 55, profitFactor: 1.5, totalTrades: 32 } },
  { id: '3', name: 'VWAP Breakout', type: 'VWAP', description: 'VWAP support/resistance bounces', is_active: false, metrics: { winRate: 58, profitFactor: 1.6, totalTrades: 28 } },
];

const strategyTypes = [
  { value: 'EMA_CROSSOVER', label: 'EMA Crossover', description: 'Trade when fast EMA crosses slow EMA' },
  { value: 'RSI', label: 'RSI Reversal', description: 'Trade RSI overbought/oversold reversals' },
  { value: 'VWAP', label: 'VWAP', description: 'Trade VWAP breakouts and bounces' },
  { value: 'MOMENTUM', label: 'Momentum', description: 'Trade with momentum indicators' },
  { value: 'BREAKOUT', label: 'Breakout', description: 'Trade price breakouts from ranges' },
  { value: 'ORB', label: 'Opening Range', description: 'Opening range breakout strategy' },
];

export default function StrategiesPage() {
  const [strategies] = useState<Strategy[]>(mockStrategies);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedType, setSelectedType] = useState('EMA_CROSSOVER');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Strategy Builder</h1>
          <p className="text-gray-500 mt-1">Create and manage your trading strategies</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          {showCreate ? 'Cancel' : '+ Create Strategy'}
        </button>
      </div>

      {showCreate && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Create New Strategy</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Strategy Name</label>
              <input type="text" placeholder="My Strategy" className="w-full px-4 py-2 border rounded-lg" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Strategy Type</label>
              <select value={selectedType} onChange={(e) => setSelectedType(e.target.value)} className="w-full px-4 py-2 border rounded-lg">
                {strategyTypes.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea placeholder="Describe your strategy..." className="w-full px-4 py-2 border rounded-lg" rows={3} />
            </div>
          </div>
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <h3 className="font-medium mb-2">Selected: {strategyTypes.find(t => t.value === selectedType)?.label}</h3>
            <p className="text-sm text-gray-600">{strategyTypes.find(t => t.value === selectedType)?.description}</p>
          </div>
          <button className="mt-4 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">Create Strategy</button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {strategies.map((strategy) => (
          <div key={strategy.id} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-semibold">{strategy.name}</h3>
                <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">{strategy.type}</span>
              </div>
              <span className={`px-2 py-1 text-xs rounded ${strategy.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                {strategy.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
            <p className="text-gray-500 text-sm mt-2">{strategy.description}</p>
            {strategy.metrics && (
              <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                <div className="bg-gray-50 rounded p-2">
                  <p className="text-xs text-gray-500">Win Rate</p>
                  <p className="font-bold text-green-600">{strategy.metrics.winRate}%</p>
                </div>
                <div className="bg-gray-50 rounded p-2">
                  <p className="text-xs text-gray-500">PF</p>
                  <p className="font-bold">{strategy.metrics.profitFactor}</p>
                </div>
                <div className="bg-gray-50 rounded p-2">
                  <p className="text-xs text-gray-500">Trades</p>
                  <p className="font-bold">{strategy.metrics.totalTrades}</p>
                </div>
              </div>
            )}
            <div className="mt-4 flex gap-2">
              <button className="flex-1 px-3 py-2 text-sm border rounded hover:bg-gray-50">Edit</button>
              <button className="flex-1 px-3 py-2 text-sm border rounded hover:bg-gray-50">Backtest</button>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Strategy Types Guide</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {strategyTypes.map((type) => (
            <div key={type.value} className="border rounded-lg p-4">
              <h3 className="font-medium">{type.label}</h3>
              <p className="text-sm text-gray-500 mt-1">{type.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
