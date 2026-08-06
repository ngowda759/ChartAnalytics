'use client';

import { useState } from 'react';

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
}

const mockOptions: OptionContract[] = [
  { id: '1', symbol: 'NIFTY', expiry: '2024-08-08', strike: 24500, type: 'CE', ltp: 245.50, change: 5.2, volume: 1250000, oi: 8900000, iv: 18.5, delta: 0.52 },
  { id: '2', symbol: 'NIFTY', expiry: '2024-08-08', strike: 24500, type: 'PE', ltp: 198.30, change: -3.1, volume: 980000, oi: 7200000, iv: 17.2, delta: -0.48 },
  { id: '3', symbol: 'NIFTY', expiry: '2024-08-08', strike: 24600, type: 'CE', ltp: 178.90, change: 4.8, volume: 850000, oi: 5600000, iv: 17.8, delta: 0.45 },
  { id: '4', symbol: 'BANKNIFTY', expiry: '2024-08-08', strike: 52500, type: 'CE', ltp: 456.75, change: 6.3, volume: 650000, oi: 4200000, iv: 19.2, delta: 0.55 },
  { id: '5', symbol: 'BANKNIFTY', expiry: '2024-08-08', strike: 52500, type: 'PE', ltp: 389.20, change: -2.5, volume: 520000, oi: 3800000, iv: 18.5, delta: -0.45 },
];

export default function OptionsPage() {
  const [options] = useState<OptionContract[]>(mockOptions);
  const [filter, setFilter] = useState<string>('all');
  const [symbol, setSymbol] = useState<string>('all');

  const filteredOptions = options.filter((opt) => {
    if (symbol !== 'all' && opt.symbol !== symbol) return false;
    if (filter !== 'all' && opt.type !== filter) return false;
    return true;
  });

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-IN').format(num);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Options Trading</h1>
          <p className="text-gray-500 mt-1">Track and analyze options contracts</p>
        </div>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          + New Strategy
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-xs text-gray-500 uppercase">Active Contracts</p>
          <p className="text-2xl font-bold">{options.length}</p>
        </div>
        <div className="bg-green-50 rounded-lg shadow p-4">
          <p className="text-xs text-green-600 uppercase">Calls (CE)</p>
          <p className="text-2xl font-bold text-green-700">
            {options.filter((o) => o.type === 'CE').length}
          </p>
        </div>
        <div className="bg-red-50 rounded-lg shadow p-4">
          <p className="text-xs text-red-600 uppercase">Puts (PE)</p>
          <p className="text-2xl font-bold text-red-700">
            {options.filter((o) => o.type === 'PE').length}
          </p>
        </div>
        <div className="bg-blue-50 rounded-lg shadow p-4">
          <p className="text-xs text-blue-600 uppercase">Total Volume</p>
          <p className="text-2xl font-bold text-blue-700">
            {formatNumber(options.reduce((acc, o) => acc + o.volume, 0))}
          </p>
        </div>
      </div>

      <div className="flex gap-4 flex-wrap">
        <select
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Symbols</option>
          <option value="NIFTY">NIFTY</option>
          <option value="BANKNIFTY">BANKNIFTY</option>
        </select>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Types</option>
          <option value="CE">Calls (CE)</option>
          <option value="PE">Puts (PE)</option>
        </select>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Expiry</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Strike</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">LTP</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Change</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Volume</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">OI</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredOptions.map((opt) => (
              <tr key={opt.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 font-medium">{opt.symbol}</td>
                <td className="px-6 py-4">{opt.expiry}</td>
                <td className="px-6 py-4">₹{opt.strike.toLocaleString()}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs rounded ${
                    opt.type === 'CE' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {opt.type}
                  </span>
                </td>
                <td className="px-6 py-4">₹{opt.ltp.toFixed(2)}</td>
                <td className={`px-6 py-4 ${opt.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {opt.change >= 0 ? '+' : ''}{opt.change}%
                </td>
                <td className="px-6 py-4">{formatNumber(opt.volume)}</td>
                <td className="px-6 py-4">{formatNumber(opt.oi)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
