'use client';

import { useState, useCallback } from 'react';
import api from '@/lib/api';
import { PositionSize, RiskCalculation, DailyLimit } from '@/types';

export function useRisk() {
  const [positionSize, setPositionSize] = useState<PositionSize | null>(null);
  const [dailyLimit, setDailyLimit] = useState<DailyLimit | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculatePositionSize = useCallback(async (params: {
    accountSize: number;
    riskPercent: number;
    entryPrice: number;
    stopLoss: number;
    instrument?: string;
  }) => {
    setLoading(true);
    setError(null);
    const response = await api.risk.calculatePositionSize({
      accountSize: params.accountSize,
      riskPercent: params.riskPercent,
      entryPrice: params.entryPrice,
      stopLoss: params.stopLoss,
      instrument: params.instrument || 'equity',
    });
    if (response.error) {
      setError(response.error);
    } else if (response.data) {
      setPositionSize({
        quantity: response.data.quantity,
        riskAmount: response.data.risk_amount,
        capitalRequired: response.data.capital_required,
        riskPercent: response.data.risk_percent,
      });
    }
    setLoading(false);
    return response;
  }, []);

  const fetchDailyLimit = useCallback(async () => {
    setLoading(true);
    const response = await api.risk.getDailyLimit();
    if (!response.error && response.data) {
      setDailyLimit({
        date: new Date(response.data.date),
        maxLoss: response.data.max_loss,
        currentLoss: response.data.current_loss,
        remainingLoss: response.data.remaining_loss,
        isLimitHit: response.data.is_limit_hit,
      });
    }
    setLoading(false);
  }, []);

  return {
    positionSize,
    dailyLimit,
    loading,
    error,
    calculatePositionSize,
    fetchDailyLimit,
  };
}

export function useRiskCalculator() {
  const [result, setResult] = useState<RiskCalculation | null>(null);
  const [loading, setLoading] = useState(false);

  const calculateRisk = useCallback(async (params: {
    entryPrice: number;
    stopLoss: number;
    target: number;
    quantity: number;
    tradeType: 'long' | 'short';
  }) => {
    setLoading(true);
    const response = await api.risk.calculateRisk(params);
    if (!response.error && response.data) {
      setResult({
        positionSize: {
          quantity: response.data.position_size.quantity,
          riskAmount: response.data.position_size.risk_amount,
          capitalRequired: response.data.position_size.capital_required,
          riskPercent: response.data.position_size.risk_percent,
        },
        maxLoss: response.data.max_loss,
        maxProfit: response.data.max_profit,
        breakeven: response.data.breakeven,
      });
    }
    setLoading(false);
    return response;
  }, []);

  return { result, loading, calculateRisk };
}
