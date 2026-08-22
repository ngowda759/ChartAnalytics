'use client';

import { useState } from 'react';
import { useJournal } from '@/hooks/useJournal';
import { IST_TIME_ZONE, parseUtc } from '@/lib/utils';

export default function JournalPage() {
  const { trades, metrics, loading, error } = useJournal();
  const [showAddTrade, setShowAddTrade] = useState(false);
  const [filter, setFilter] = useState<'all' | 'open' | 'closed'>('all');

  const filteredTrades = trades.filter((trade) => {
    if (filter === 'all') return true;
    return trade.status === filter;
  });

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatDate = (date: Date | string) => {
    return parseUtc(date).toLocaleDateString('en-IN', {
      timeZone: IST_TIME_ZONE,
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'bg-blue-100 text-blue-800';
      case 'closed':
        return 'bg-green-100 text-green-800';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getPnLColor = (pnl?: number) => {
    if (pnl === undefined) return 'text-gray-500';
    return pnl >= 0 ? 'text-green-600' : 'text-red-600';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Trade Journal</h1>
          <p className="text-gray-500 mt-1">Track and analyze your trading performance</p>
        </div>
        <button
          onClick={() => setShowAddTrade(!showAddTrade)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          {showAddTrade ? 'Cancel' : '+ Add Trade'}
        </button>
      </div>

      {/* Performance Metrics */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <MetricCard
            title="Total P&L"
            value={formatCurrency(metrics.totalPnl)}
            color={metrics.totalPnl >= 0 ? 'green' : 'red'}
          />
          <MetricCard title="Win Rate" value={`${metrics.winRate.toFixed(1)}%`} />
          <MetricCard title="Total Trades" value={metrics.totalTrades.toString()} />
          <MetricCard title="Avg Win" value={formatCurrency(metrics.averageWin)} color="green" />
          <MetricCard title="Avg Loss" value={formatCurrency(metrics.averageLoss)} color="red" />
          <MetricCard title="Profit Factor" value={metrics.profitFactor.toFixed(2)} />
          <MetricCard
            title="Sharpe Ratio"
            value={metrics.sharpeRatio !== null ? metrics.sharpeRatio.toFixed(2) : 'N/A'}
          />
          <MetricCard
            title="Max Drawdown"
            value={
              metrics.maxDrawdownPercent !== null
                ? `${metrics.maxDrawdownPercent.toFixed(1)}%`
                : 'N/A'
            }
            color="red"
          />
          <MetricCard title="Expectancy" value={formatCurrency(metrics.expectancy)} />
          <MetricCard
            title="Avg R:R"
            value={metrics.avgRr !== null ? `${metrics.avgRr.toFixed(2)}:1` : 'N/A'}
          />
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-2">
        {(['all', 'open', 'closed'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg transition-colors ${
              filter === f
                ? 'bg-blue-100 text-blue-700 border border-blue-300'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Trades List */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Symbol
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Entry
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Exit
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Strategy
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                P&L
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Date
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredTrades.map((trade) => (
              <tr key={trade.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="font-medium text-gray-900">{trade.symbol}</span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${
                      trade.type === 'long'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {trade.type.toUpperCase()}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatCurrency(trade.entry.price)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {trade.exit ? formatCurrency(trade.exit.price) : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {trade.strategy}
                </td>
                <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${getPnLColor(trade.pnl)}`}>
                  {trade.pnl !== undefined ? formatCurrency(trade.pnl) : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(trade.status)}`}>
                    {trade.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDate(trade.createdAt)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredTrades.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">No trades found</p>
        </div>
      )}
    </div>
  );
}

function MetricCard({
  title,
  value,
  color = 'gray',
}: {
  title: string;
  value: string;
  color?: 'gray' | 'green' | 'red';
}) {
  const colorClasses = {
    gray: 'text-gray-900',
    green: 'text-green-600',
    red: 'text-red-600',
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{title}</p>
      <p className={`text-xl font-bold mt-1 ${colorClasses[color]}`}>{value}</p>
    </div>
  );
}
