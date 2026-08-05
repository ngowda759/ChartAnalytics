'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { Trade, PerformanceMetrics } from '@/types';

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
      setTrades(response.data || []);
    }
    setLoading(false);
  }, []);

  const fetchMetrics = useCallback(async () => {
    const response = await api.journal.getPerformance();
    if (!response.error) {
      setMetrics(response.data);
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
