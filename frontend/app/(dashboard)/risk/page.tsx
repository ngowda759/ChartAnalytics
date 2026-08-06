'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertTriangle, TrendingUp, TrendingDown, Shield, Calculator } from 'lucide-react';

interface PositionSize {
  quantity: number;
  riskAmount: number;
  capitalRequired: number;
  riskPercent: number;
}

interface DailyLimit {
  maxLoss: number;
  currentLoss: number;
  remainingLoss: number;
  isLimitHit: boolean;
}

export default function RiskPage() {
  const [accountSize, setAccountSize] = useState(100000);
  const [riskPercent, setRiskPercent] = useState(2);
  const [entryPrice, setEntryPrice] = useState(24500);
  const [stopLoss, setStopLoss] = useState(24300);
  const [instrument, setInstrument] = useState('equity');
  const [positionSize, setPositionSize] = useState<PositionSize | null>(null);
  const [calculating, setCalculating] = useState(false);
  
  // Mock daily limit data
  const [dailyLimit] = useState<DailyLimit>({
    maxLoss: 5000,
    currentLoss: 1500,
    remainingLoss: 3500,
    isLimitHit: false,
  });

  const calculatePosition = async () => {
    setCalculating(true);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 500));
    
    const priceDiff = Math.abs(entryPrice - stopLoss);
    const riskAmount = accountSize * (riskPercent / 100);
    const quantity = Math.floor(riskAmount / priceDiff);
    const capitalRequired = quantity * entryPrice;
    
    setPositionSize({
      quantity,
      riskAmount,
      capitalRequired,
      riskPercent,
    });
    
    setCalculating(false);
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatINR = (value: number) => {
    return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(value);
  };

  const priceDifference = Math.abs(entryPrice - stopLoss);
  const riskAmount = accountSize * (riskPercent / 100);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Risk Management</h1>
        <p className="text-muted-foreground">Calculate position sizes and manage your trading risk</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Position Size Calculator */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calculator className="h-5 w-5" />
              Position Size Calculator
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Account Size (₹)</label>
              <input
                type="number"
                value={accountSize}
                onChange={(e) => setAccountSize(Number(e.target.value))}
                className="w-full px-4 py-2 border rounded-lg bg-background"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Risk Percentage (%) - Max 2% recommended
              </label>
              <input
                type="number"
                value={riskPercent}
                onChange={(e) => setRiskPercent(Number(e.target.value))}
                min="0.5"
                max="10"
                step="0.5"
                className="w-full px-4 py-2 border rounded-lg bg-background"
              />
              <div className="mt-2">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-muted-foreground">Risk Amount:</span>
                  <span className="font-medium text-red-600">{formatCurrency(riskAmount)}</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      riskPercent <= 1 ? 'bg-green-500' : riskPercent <= 2 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${Math.min(riskPercent * 10, 100)}%` }}
                  />
                </div>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Entry Price (₹)</label>
              <input
                type="number"
                value={entryPrice}
                onChange={(e) => setEntryPrice(Number(e.target.value))}
                className="w-full px-4 py-2 border rounded-lg bg-background"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Stop Loss (₹)</label>
              <input
                type="number"
                value={stopLoss}
                onChange={(e) => setStopLoss(Number(e.target.value))}
                className="w-full px-4 py-2 border rounded-lg bg-background"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Instrument Type</label>
              <select
                value={instrument}
                onChange={(e) => setInstrument(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg bg-background"
              >
                <option value="equity">Equity</option>
                <option value="futures">Futures</option>
                <option value="options">Options</option>
              </select>
            </div>
            <Button 
              onClick={calculatePosition} 
              disabled={calculating}
              className="w-full"
            >
              {calculating ? 'Calculating...' : 'Calculate Position Size'}
            </Button>

            {/* Results */}
            {positionSize && (
              <div className="mt-6 p-4 bg-muted rounded-lg border">
                <h3 className="font-semibold mb-3">Results</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center p-3 bg-background rounded-lg">
                    <p className="text-xs text-muted-foreground mb-1">Quantity</p>
                    <p className="text-2xl font-bold">{positionSize.quantity}</p>
                  </div>
                  <div className="text-center p-3 bg-red-500/10 rounded-lg">
                    <p className="text-xs text-muted-foreground mb-1">Risk Amount</p>
                    <p className="text-2xl font-bold text-red-600">{formatCurrency(positionSize.riskAmount)}</p>
                  </div>
                  <div className="text-center p-3 bg-background rounded-lg">
                    <p className="text-xs text-muted-foreground mb-1">Capital Required</p>
                    <p className="text-xl font-bold">{formatCurrency(positionSize.capitalRequired)}</p>
                  </div>
                  <div className="text-center p-3 bg-background rounded-lg">
                    <p className="text-xs text-muted-foreground mb-1">Price Diff</p>
                    <p className="text-xl font-bold">₹{priceDifference}</p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Daily Loss Limit */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Daily Loss Limit
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-3 bg-red-500/10 rounded-lg">
                  <p className="text-xs text-muted-foreground mb-1">Max Loss</p>
                  <p className="text-xl font-bold text-red-600">{formatCurrency(dailyLimit.maxLoss)}</p>
                </div>
                <div className="text-center p-3 bg-yellow-500/10 rounded-lg">
                  <p className="text-xs text-muted-foreground mb-1">Current Loss</p>
                  <p className="text-xl font-bold text-yellow-600">{formatCurrency(dailyLimit.currentLoss)}</p>
                </div>
                <div className="text-center p-3 bg-green-500/10 rounded-lg">
                  <p className="text-xs text-muted-foreground mb-1">Remaining</p>
                  <p className="text-xl font-bold text-green-600">{formatCurrency(dailyLimit.remainingLoss)}</p>
                </div>
              </div>
              <div className="w-full bg-muted rounded-full h-4">
                <div
                  className={`h-4 rounded-full ${
                    dailyLimit.currentLoss / dailyLimit.maxLoss < 0.5
                      ? 'bg-green-500'
                      : dailyLimit.currentLoss / dailyLimit.maxLoss < 0.8
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
                  }`}
                  style={{ width: `${Math.min((dailyLimit.currentLoss / dailyLimit.maxLoss) * 100, 100)}%` }}
                />
              </div>
              {dailyLimit.isLimitHit && (
                <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg">
                  <p className="text-red-600 font-medium flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    Daily loss limit reached! Stop trading for today.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Risk Guidelines */}
          <Card>
            <CardHeader>
              <CardTitle>Risk Management Guidelines</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                <li className="flex items-start gap-3">
                  <span className="flex-shrink-0 h-6 w-6 rounded-full bg-green-500/10 text-green-600 flex items-center justify-center text-sm font-medium">1</span>
                  <div>
                    <p className="font-medium">Risk 1-2% Per Trade</p>
                    <p className="text-sm text-muted-foreground">Never risk more than 2% of your capital on a single trade</p>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className="flex-shrink-0 h-6 w-6 rounded-full bg-green-500/10 text-green-600 flex items-center justify-center text-sm font-medium">2</span>
                  <div>
                    <p className="font-medium">Daily Loss Limit</p>
                    <p className="text-sm text-muted-foreground">Set a maximum daily loss (e.g., 5%) and stop trading when reached</p>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className="flex-shrink-0 h-6 w-6 rounded-full bg-green-500/10 text-green-600 flex items-center justify-center text-sm font-medium">3</span>
                  <div>
                    <p className="font-medium">Risk-Reward Ratio</p>
                    <p className="text-sm text-muted-foreground">Aim for at least 2:1 risk-reward ratio on your trades</p>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className="flex-shrink-0 h-6 w-6 rounded-full bg-green-500/10 text-green-600 flex items-center justify-center text-sm font-medium">4</span>
                  <div>
                    <p className="font-medium">Position Sizing</p>
                    <p className="text-sm text-muted-foreground">Calculate position size based on your stop loss, not vice versa</p>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className="flex-shrink-0 h-6 w-6 rounded-full bg-green-500/10 text-green-600 flex items-center justify-center text-sm font-medium">5</span>
                  <div>
                    <p className="font-medium">No Revenge Trading</p>
                    <p className="text-sm text-muted-foreground">Never try to recover losses by taking larger positions</p>
                  </div>
                </li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
