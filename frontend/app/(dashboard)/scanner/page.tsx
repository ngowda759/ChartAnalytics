'use client';

import { useState } from 'react';

interface ScanResult {
  id: string;
  symbol: string;
  name?: string;
  scan_type: string;
  direction: string;
  confidence: number;
  price: number;
  change_percent: number;
  volume_ratio: number;
  timestamp: string;
}

const mockScanResults: ScanResult[] = [
  { id: '1', symbol: 'RELIANCE', name: 'Reliance Industries', scan_type: 'breakout', direction: 'bullish', confidence: 85, price: 2987.50, change_percent: 2.3, volume_ratio: 2.1, timestamp: new Date().toISOString() },
  { id: '2', symbol: 'HDFCBANK', name: 'HDFC Bank', scan_type: 'ema_cross', direction: 'bullish', confidence: 78, price: 1695.20, change_percent: 1.5, volume_ratio: 1.8, timestamp: new Date().toISOString() },
  { id: '3', symbol: 'NIFTY', name: 'NIFTY 50', scan_type: 'volume_spike', direction: 'neutral', confidence: 72, price: 24580.35, change_percent: 0.8, volume_ratio: 2.5, timestamp: new Date().toISOString() },
  { id: '4', symbol: 'ICICIBANK', name: 'ICICI Bank', scan_type: 'oi_buildup', direction: 'bearish', confidence: 68, price: 1120.45, change_percent: -1.2, volume_ratio: 1.6, timestamp: new Date().toISOString() },
  { id: '5', symbol: 'TCS', name: 'Tata Consultancy', scan_type: 'breakout', direction: 'bullish', confidence: 82, price: 4150.80, change_percent: 1.8, volume_ratio: 1.9, timestamp: new Date().toISOString() },
];

export default function ScannerPage() {
  const [results] = useState<ScanResult[]>(mockScanResults);
  const [filter, setFilter] = useState<string>('all');
  const [scanType, setScanType] = useState<string>('all');

  const filteredResults = results.filter((r) => {
    if (filter !== 'all' && r.direction !== filter) return false;
    if (scanType !== 'all' && r.scan_type !== scanType) return false;
    return true;
  });

  const bullishCount = results.filter((r) => r.direction === 'bullish').length;
  const bearishCount = results.filter((r) => r.direction === 'bearish').length;

  const getDirectionColor = (direction: string) => {
    switch (direction) {
      case 'bullish': return 'text-green-600 bg-green-50';
      case 'bearish': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Market Scanner</h1>
          <p className="text-gray-500 mt-1">Find trading opportunities in real-time</p>
        </div>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Run Scan</button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-xs text-gray-500 uppercase">Total Signals</p>
          <p className="text-2xl font-bold">{results.length}</p>
        </div>
        <div className="bg-green-50 rounded-lg shadow p-4">
          <p className="text-xs text-green-600 uppercase">Bullish</p>
          <p className="text-2xl font-bold text-green-700">{bullishCount}</p>
        </div>
        <div className="bg-red-50 rounded-lg shadow p-4">
          <p className="text-xs text-red-600 uppercase">Bearish</p>
          <p className="text-2xl font-bold text-red-700">{bearishCount}</p>
        </div>
        <div className="bg-gray-50 rounded-lg shadow p-4">
          <p className="text-xs text-gray-600 uppercase">Neutral</p>
          <p className="text-2xl font-bold text-gray-700">{results.length - bullishCount - bearishCount}</p>
        </div>
      </div>

      <div className="flex gap-4 flex-wrap">
        <select value={filter} onChange={(e) => setFilter(e.target.value)} className="px-4 py-2 border rounded-lg">
          <option value="all">All Directions</option>
          <option value="bullish">Bullish</option>
          <option value="bearish">Bearish</option>
        </select>
        <select value={scanType} onChange={(e) => setScanType(e.target.value)} className="px-4 py-2 border rounded-lg">
          <option value="all">All Types</option>
          <option value="breakout">Breakout</option>
          <option value="ema_cross">EMA Cross</option>
          <option value="volume_spike">Volume Spike</option>
        </select>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Direction</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Change</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Confidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredResults.map((r) => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-6 py-4"><span className="font-medium">{r.symbol}</span></td>
                <td className="px-6 py-4"><span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">{r.scan_type}</span></td>
                <td className="px-6 py-4"><span className={`px-2 py-1 text-xs rounded ${getDirectionColor(r.direction)}`}>{r.direction}</span></td>
                <td className="px-6 py-4">₹{r.price.toLocaleString()}</td>
                <td className={`px-6 py-4 ${r.change_percent >= 0 ? 'text-green-600' : 'text-red-600'}`}>{r.change_percent >= 0 ? '+' : ''}{r.change_percent}%</td>
                <td className="px-6 py-4 font-bold">{r.confidence}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
