'use client';

import { useState } from 'react';

interface Indicator {
  id: string;
  name: string;
  type: string;
  description: string;
  defaultPeriod: number;
  category: 'trend' | 'momentum' | 'volatility' | 'volume';
}

const indicators: Indicator[] = [
  { id: '1', name: 'SMA', type: 'Simple Moving Average', description: 'Average price over a specified period', defaultPeriod: 20, category: 'trend' },
  { id: '2', name: 'EMA', type: 'Exponential Moving Average', description: 'Weighted average giving more weight to recent prices', defaultPeriod: 12, category: 'trend' },
  { id: '3', name: 'RSI', type: 'Relative Strength Index', description: 'Measures speed and change of price movements', defaultPeriod: 14, category: 'momentum' },
  { id: '4', name: 'MACD', type: 'Moving Average Convergence Divergence', description: 'Shows relationship between two moving averages', defaultPeriod: 26, category: 'momentum' },
  { id: '5', name: 'Bollinger Bands', type: 'Bollinger Bands', description: 'Volatility bands placed above and below a moving average', defaultPeriod: 20, category: 'volatility' },
  { id: '6', name: 'ATR', type: 'Average True Range', description: 'Measures market volatility', defaultPeriod: 14, category: 'volatility' },
  { id: '7', name: 'VWAP', type: 'Volume Weighted Average Price', description: 'Average price weighted by volume', defaultPeriod: 1, category: 'volume' },
  { id: '8', name: 'OBV', type: 'On Balance Volume', description: 'Volume-based momentum indicator', defaultPeriod: 1, category: 'volume' },
  { id: '9', name: 'Stochastic', type: 'Stochastic Oscillator', description: 'Momentum indicator comparing closing price to price range', defaultPeriod: 14, category: 'momentum' },
  { id: '10', name: 'ADX', type: 'Average Directional Index', description: 'Measures trend strength', defaultPeriod: 14, category: 'trend' },
];

export default function IndicatorsPage() {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const filteredIndicators = indicators.filter((ind) => {
    if (selectedCategory !== 'all' && ind.category !== selectedCategory) return false;
    if (searchTerm && !ind.name.toLowerCase().includes(searchTerm.toLowerCase()) && 
        !ind.type.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'trend': return 'bg-blue-100 text-blue-800';
      case 'momentum': return 'bg-purple-100 text-purple-800';
      case 'volatility': return 'bg-orange-100 text-orange-800';
      case 'volume': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Technical Indicators</h1>
          <p className="text-gray-500 mt-1">Configure and manage technical analysis indicators</p>
        </div>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          + Add Indicator
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-xs text-gray-500 uppercase">Total Indicators</p>
          <p className="text-2xl font-bold">{indicators.length}</p>
        </div>
        <div className="bg-blue-50 rounded-lg shadow p-4">
          <p className="text-xs text-blue-600 uppercase">Trend</p>
          <p className="text-2xl font-bold text-blue-700">
            {indicators.filter((i) => i.category === 'trend').length}
          </p>
        </div>
        <div className="bg-purple-50 rounded-lg shadow p-4">
          <p className="text-xs text-purple-600 uppercase">Momentum</p>
          <p className="text-2xl font-bold text-purple-700">
            {indicators.filter((i) => i.category === 'momentum').length}
          </p>
        </div>
        <div className="bg-orange-50 rounded-lg shadow p-4">
          <p className="text-xs text-orange-600 uppercase">Volatility</p>
          <p className="text-2xl font-bold text-orange-700">
            {indicators.filter((i) => i.category === 'volatility').length}
          </p>
        </div>
        <div className="bg-green-50 rounded-lg shadow p-4">
          <p className="text-xs text-green-600 uppercase">Volume</p>
          <p className="text-2xl font-bold text-green-700">
            {indicators.filter((i) => i.category === 'volume').length}
          </p>
        </div>
      </div>

      <div className="flex gap-4 flex-wrap">
        <input
          type="text"
          placeholder="Search indicators..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 w-64"
        />
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Categories</option>
          <option value="trend">Trend</option>
          <option value="momentum">Momentum</option>
          <option value="volatility">Volatility</option>
          <option value="volume">Volume</option>
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredIndicators.map((ind) => (
          <div key={ind.id} className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{ind.name}</h3>
                <p className="text-sm text-gray-500">{ind.type}</p>
              </div>
              <span className={`px-2 py-1 text-xs rounded ${getCategoryColor(ind.category)}`}>
                {ind.category}
              </span>
            </div>
            <p className="text-gray-600 text-sm mb-4">{ind.description}</p>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">
                Default Period: <span className="font-medium">{ind.defaultPeriod}</span>
              </span>
              <div className="flex gap-2">
                <button className="px-3 py-1 text-sm border rounded hover:bg-gray-50">Edit</button>
                <button className="px-3 py-1 text-sm border rounded hover:bg-gray-50">Apply</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
