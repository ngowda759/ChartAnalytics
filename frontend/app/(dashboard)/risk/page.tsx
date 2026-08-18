'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertTriangle, Shield, Calculator, RefreshCw } from 'lucide-react';
import { riskApi } from '@/lib/api';

interface PositionSize {
  quantity: number;
  risk_amount: number;
  capital_required: number;
  risk_percent: number;
}

interface DailyLimit {
  date: string;
  max_loss: number;
  current_loss: number;
  remaining_loss: number;
  is_limit_hit: boolean;
}

export default function RiskPage() {
  const [accountSize, setAccountSize] = useState(100000);
  const [riskPercent, setRiskPercent] = useState(2);
  const [entryPrice, setEntryPrice] = useState(24500);
  const [stopLoss, setStopLoss] = useState(24300);
  const [instrument, setInstrument] = useState('equity');
  const [positionSize, setPositionSize] = useState<PositionSize | null>(null);
  const [calculating, setCalculating] = useState(false);
  const [calcError, setCalcError] = useState<string | null>(null);

  // Daily loss limit comes from the backend (/risk/daily-limit), which truthfully
  // reports current_loss = 0 when no broker P&L feed is connected — never a
  // fabricated number.
  const [dailyLimit, setDailyLimit] = useState<DailyLimit | null>(null);
  const [limitLoading, setLimitLoading] = useState(true);
  const [limitError, setLimitError] = useState<string | null>(null);

  const loadDailyLimit = useCallback(async () => {
    setLimitLoading(true);
    setLimitError(null);
    const res = await riskApi.getDailyLimit();
    if (res.error || !res.data) {
      setLimitError(res.error ?? 'Daily limit unavailable');
      setDailyLimit(null);
    } else {
      setDailyLimit(res.data as DailyLimit);
    }
    setLimitLoading(false);
  }, []);

  useEffect(() => {
    loadDailyLimit();
  }, [loadDailyLimit]);

  const calculatePosition = async () => {
    setCalculating(true);
    setCalcError(null);
    const res = await riskApi.calculatePositionSize({
      accountSize,
      riskPercent,
      entryPrice,
      stopLoss,
      instrument,
    });
    if (res.error || !res.data) {
      setCalcError(res.error ?? 'Could not compute position size');
      setPositionSize(null);
    } else {
      setPositionSize(res.data as PositionSize);
    }
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

  const riskAmount = accountSize * (riskPercent / 100);
  const priceDifference = Math.abs(entryPrice - stopLoss);

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

            {calcError && (
              <p className="mt-4 text-sm text-red-600">{calcError}</p>
            )}

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
                    <p className="text-2xl font-bold text-red-600">{formatCurrency(positionSize.risk_amount)}</p>
                  </div>
                  <div className="text-center p-3 bg-background rounded-lg">
                    <p className="text-xs text-muted-foreground mb-1">Capital Required</p>
                    <p className="text-xl font-bold">{formatCurrency(positionSize.capital_required)}</p>
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
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Daily Loss Limit
                </CardTitle>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={loadDailyLimit} disabled={limitLoading}>
                  <RefreshCw className={`h-4 w-4 ${limitLoading ? 'animate-spin' : ''}`} />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {limitLoading ? (
                <div className="flex justify-center py-6">
                  <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : limitError || !dailyLimit ? (
                <div className="flex flex-col items-center justify-center py-6 text-center gap-2">
                  <AlertTriangle className="h-8 w-8 text-muted-foreground/50" />
                  <p className="text-sm text-muted-foreground">
                    {limitError ?? 'Daily limit unavailable'}
                  </p>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-3 bg-red-500/10 rounded-lg">
                      <p className="text-xs text-muted-foreground mb-1">Max Loss</p>
                      <p className="text-xl font-bold text-red-600">{formatCurrency(dailyLimit.max_loss)}</p>
                    </div>
                    <div className="text-center p-3 bg-yellow-500/10 rounded-lg">
                      <p className="text-xs text-muted-foreground mb-1">Current Loss</p>
                      <p className="text-xl font-bold text-yellow-600">{formatCurrency(dailyLimit.current_loss)}</p>
                    </div>
                    <div className="text-center p-3 bg-green-500/10 rounded-lg">
                      <p className="text-xs text-muted-foreground mb-1">Remaining</p>
                      <p className="text-xl font-bold text-green-600">{formatCurrency(dailyLimit.remaining_loss)}</p>
                    </div>
                  </div>
                  <div className="w-full bg-muted rounded-full h-4">
                    <div
                      className={`h-4 rounded-full ${
                        dailyLimit.current_loss / dailyLimit.max_loss < 0.5
                          ? 'bg-green-500'
                          : dailyLimit.current_loss / dailyLimit.max_loss < 0.8
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                      }`}
                      style={{ width: `${Math.min((dailyLimit.current_loss / dailyLimit.max_loss) * 100, 100)}%` }}
                    />
                  </div>
                  {dailyLimit.is_limit_hit && (
                    <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg">
                      <p className="text-red-600 font-medium flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4" />
                        Daily loss limit reached! Stop trading for today.
                      </p>
                    </div>
                  )}
                </>
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
