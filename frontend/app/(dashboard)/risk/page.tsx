'use client';

import { useState, useEffect } from 'react';
import { useRisk } from '@/hooks/useRisk';

export default function RiskPage() {
  const { positionSize, dailyLimit, loading, error, calculatePositionSize, fetchDailyLimit } = useRisk();
  const [accountSize, setAccountSize] = useState(100000);
  const [riskPercent, setRiskPercent] = useState(2);
  const [entryPrice, setEntryPrice] = useState(25000);
  const [stopLoss, setStopLoss] = useState(24800);
  const [instrument, setInstrument] = useState('equity');

  useEffect(() => {
    fetchDailyLimit();
  }, [fetchDailyLimit]);

  const handleCalculate = async () => {
    await calculatePositionSize({
      accountSize,
      riskPercent,
      entryPrice,
      stopLoss,
      instrument,
    });
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const riskAmount = accountSize * (riskPercent / 100);
  const priceDifference = Math.abs(entryPrice - stopLoss);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Risk Management</h1>
        <p className="text-gray-500 mt-1">
          Calculate position sizes and manage your trading risk
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Position Size Calculator */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Position Size Calculator
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Account Size (₹)
              </label>
              <input
                type="number"
                value={accountSize}
                onChange={(e) => setAccountSize(Number(e.target.value))}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Risk Percentage (%) - Max 2% recommended
              </label>
              <input
                type="number"
                value={riskPercent}
                onChange={(e) => setRiskPercent(Number(e.target.value))}
                min="0.5"
                max="10"
                step="0.5"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <div className="mt-2">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>Risk Amount:</span>
                  <span className="font-medium text-red-600">{formatCurrency(riskAmount)}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      riskPercent <= 1 ? 'bg-green-500' : riskPercent <= 2 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${Math.min(riskPercent * 10, 100)}%` }}
                  ></div>
                </div>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Entry Price (₹)
              </label>
              <input
                type="number"
                value={entryPrice}
                onChange={(e) => setEntryPrice(Number(e.target.value))}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Stop Loss (₹)
              </label>
              <input
                type="number"
                value={stopLoss}
                onChange={(e) => setStopLoss(Number(e.target.value))}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Instrument Type
              </label>
              <select
                value={instrument}
                onChange={(e) => setInstrument(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="equity">Equity</option>
                <option value="futures">Futures</option>
                <option value="options">Options</option>
              </select>
            </div>
            <button
              onClick={handleCalculate}
              disabled={loading}
              className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {loading ? 'Calculating...' : 'Calculate Position Size'}
            </button>
          </div>

          {/* Results */}
          {positionSize && (
            <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <h3 className="font-semibold text-blue-900 mb-3">Results</h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Quantity:</span>
                  <span className="font-bold text-lg">{positionSize.quantity}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Risk Amount:</span>
                  <span className="font-medium text-red-600">
                    {formatCurrency(positionSize.riskAmount)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Capital Required:</span>
                  <span className="font-medium">
                    {formatCurrency(positionSize.capitalRequired)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Risk per Trade:</span>
                  <span className="font-medium">{positionSize.riskPercent.toFixed(2)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Price Difference:</span>
                  <span className="font-medium">{formatCurrency(priceDifference)}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Daily Loss Limit */}
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Daily Loss Limit
            </h2>
            {dailyLimit && (
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Maximum Allowed Loss:</span>
                  <span className="font-bold text-lg text-red-600">
                    {formatCurrency(dailyLimit.maxLoss)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Current Loss:</span>
                  <span className="font-medium">
                    {formatCurrency(dailyLimit.currentLoss)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Remaining Allowance:</span>
                  <span className={`font-medium ${dailyLimit.remainingLoss < 1000 ? 'text-red-600' : 'text-green-600'}`}>
                    {formatCurrency(dailyLimit.remainingLoss)}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4">
                  <div
                    className={`h-4 rounded-full ${
                      dailyLimit.currentLoss / dailyLimit.maxLoss < 0.5
                        ? 'bg-green-500'
                        : dailyLimit.currentLoss / dailyLimit.maxLoss < 0.8
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    }`}
                    style={{
                      width: `${Math.min(
                        (dailyLimit.currentLoss / dailyLimit.maxLoss) * 100,
                        100
                      )}%`,
                    }}
                  ></div>
                </div>
                {dailyLimit.isLimitHit && (
                  <div className="p-4 bg-red-100 border border-red-300 rounded-lg">
                    <p className="text-red-800 font-medium">
                      ⚠️ Daily loss limit reached! Stop trading for today.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Risk Guidelines */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Risk Management Guidelines
            </h2>
            <ul className="space-y-3">
              <li className="flex items-start">
                <span className="flex-shrink-0 h-6 w-6 rounded-full bg-green-100 text-green-600 flex items-center justify-center mr-3">
                  1
                </span>
                <div>
                  <p className="font-medium text-gray-900">Risk 1-2% Per Trade</p>
                  <p className="text-sm text-gray-500">
                    Never risk more than 2% of your capital on a single trade
                  </p>
                </div>
              </li>
              <li className="flex items-start">
                <span className="flex-shrink-0 h-6 w-6 rounded-full bg-green-100 text-green-600 flex items-center justify-center mr-3">
                  2
                </span>
                <div>
                  <p className="font-medium text-gray-900">Daily Loss Limit</p>
                  <p className="text-sm text-gray-500">
                    Set a maximum daily loss (e.g., 5%) and stop trading when reached
                  </p>
                </div>
              </li>
              <li className="flex items-start">
                <span className="flex-shrink-0 h-6 w-6 rounded-full bg-green-100 text-green-600 flex items-center justify-center mr-3">
                  3
                </span>
                <div>
                  <p className="font-medium text-gray-900">Risk-Reward Ratio</p>
                  <p className="text-sm text-gray-500">
                    Aim for at least 2:1 risk-reward ratio on your trades
                  </p>
                </div>
              </li>
              <li className="flex items-start">
                <span className="flex-shrink-0 h-6 w-6 rounded-full bg-green-100 text-green-600 flex items-center justify-center mr-3">
                  4
                </span>
                <div>
                  <p className="font-medium text-gray-900">Position Sizing</p>
                  <p className="text-sm text-gray-500">
                    Calculate position size based on your stop loss, not vice versa
                  </p>
                </div>
              </li>
              <li className="flex items-start">
                <span className="flex-shrink-0 h-6 w-6 rounded-full bg-green-100 text-green-600 flex items-center justify-center mr-3">
                  5
                </span>
                <div>
                  <p className="font-medium text-gray-900">No Revenge Trading</p>
                  <p className="text-sm text-gray-500">
                    Never try to recover losses by taking larger positions
                  </p>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
