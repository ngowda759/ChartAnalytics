'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { Trade, PerformanceMetrics, MonthlyReturn } from '@/types';

// Backend returns snake_case (FastAPI/pydantic); the app uses camelCase.
// Nullable metric fields (sharpe/drawdown/avg_rr) are truthfully null when
// not derivable from the trade list — map them through as null, never 0.
function mapMonthlyReturn(raw: any): MonthlyReturn {
  return {
    month: raw?.month ?? '',
    return: raw?.return ?? 0,
    trades: raw?.trades ?? 0,
  };
}

function toPerformanceMetrics(raw: any): PerformanceMetrics | null {
  if (!raw || typeof raw !== 'object') return null;
  const num = (v: any) => (typeof v === 'number' && Number.isFinite(v) ? v : 0);
  const numOrNull = (v: any) =>
    typeof v === 'number' && Number.isFinite(v) ? v : null;
  return {
    totalTrades: num(raw.total_trades ?? raw.totalTrades),
    winningTrades: num(raw.winning_trades ?? raw.winningTrades),
    losingTrades: num(raw.losing_trades ?? raw.losingTrades),
    winRate: num(raw.win_rate ?? raw.winRate),
    averageWin: num(raw.average_win ?? raw.averageWin),
    averageLoss: num(raw.average_loss ?? raw.averageLoss),
    profitFactor: num(raw.profit_factor ?? raw.profitFactor),
    sharpeRatio: numOrNull(raw.sharpe_ratio ?? raw.sharpeRatio),
    maxDrawdown: numOrNull(raw.max_drawdown ?? raw.maxDrawdown),
    maxDrawdownPercent: numOrNull(
      raw.max_drawdown_percent ?? raw.maxDrawdownPercent
    ),
    totalPnl: num(raw.total_pnl ?? raw.totalPnl),
    expectancy: num(raw.expectancy),
    avgRr: numOrNull(raw.avg_rr ?? raw.avgRr),
    monthlyReturns: Array.isArray(raw.monthly_returns ?? raw.monthlyReturns)
      ? (raw.monthly_returns ?? raw.monthlyReturns).map(mapMonthlyReturn)
      : [],
  };
}

// Backend trades are snake_case; map the fields the UI touches so rows
// never read undefined (entry.price, createdAt, userId, ...).
function toTrade(raw: any): Trade {
  const entry = raw?.entry ?? {};
  const exit = raw?.exit ?? undefined;
  return {
    ...raw,
    userId: raw?.user_id ?? raw?.userId ?? '',
    entry: {
      price: entry.price ?? 0,
      quantity: entry.quantity ?? 0,
      timestamp: entry.timestamp ?? null,
    },
    exit: exit
      ? {
          price: exit.price ?? 0,
          quantity: exit.quantity ?? 0,
          timestamp: exit.timestamp ?? null,
        }
      : undefined,
    createdAt: raw?.created_at ?? raw?.createdAt ?? '',
    updatedAt: raw?.updated_at ?? raw?.updatedAt ?? '',
  } as Trade;
}

export function useJournal() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTrades = useCallback(async () => {
    setLoading(true);
    const response = await api.journal.getTrades();
    if (response.error) {
      setError(response.error);
    } else {
      setTrades((response.data || []).map(toTrade));
    }
    setLoading(false);
  }, []);

  const fetchMetrics = useCallback(async () => {
    const response = await api.journal.getPerformance();
    if (!response.error) {
      setMetrics(toPerformanceMetrics(response.data));
    }
  }, []);

  useEffect(() => {
    fetchTrades();
    fetchMetrics();
  }, [fetchTrades, fetchMetrics]);

  const createTrade = async (trade: Partial<Trade>) => {
    const response = await api.journal.createTrade(trade);
    if (!response.error) {
      await fetchTrades();
    }
    return response;
  };

  const updateTrade = async (tradeId: string, updates: Partial<Trade>) => {
    const response = await api.journal.updateTrade(tradeId, updates);
    if (!response.error) {
      await fetchTrades();
      await fetchMetrics();
    }
    return response;
  };

  return {
    trades,
    metrics,
    loading,
    error,
    fetchTrades,
    fetchMetrics,
    createTrade,
    updateTrade,
  };
}

export function useTradeReview(tradeId: string) {
  const [review, setReview] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitTradeForReview = async (tradeData: any) => {
    setLoading(true);
    setError(null);
    const response = await api.ai.reviewTrade(tradeData);
    if (response.error) {
      setError(response.error);
    } else {
      setReview(response.data);
    }
    setLoading(false);
    return response;
  };

  return { review, loading, error, submitTradeForReview };
}

export function useChartAnalysis() {
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyzeChart = async (chartData: {
    symbol: string;
    highs: number[];
    lows: number[];
    closes: number[];
    volumes: number[];
    timestamps: string[];
  }) => {
    setLoading(true);
    setError(null);
    const response = await api.ai.analyzePatterns(chartData);
    if (response.error) {
      setError(response.error);
    } else {
      setAnalysis(response.data);
    }
    setLoading(false);
    return response;
  };

  return { analysis, loading, error, analyzeChart };
}
