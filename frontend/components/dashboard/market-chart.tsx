'use client';

import { useEffect, useRef, useState } from 'react';
import { marketApi } from '@/lib/api';

interface MarketChartProps {
  symbol: string;
}

interface CandleData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface VolumeData {
  time: number;
  value: number;
  color: string;
}

// Backend /market/indices returns index rows under these symbols; map the
// short labels used by the dashboard to the matching index row.
const INDEX_SYMBOL_MAP: Record<string, string[]> = {
  NIFTY: ['NIFTY 50', 'NIFTY50'],
  BANKNIFTY: ['NIFTY BANK', 'BANK NIFTY'],
  FINNIFTY: ['NIFTY FIN SERVICE', 'NIFTY FIN SERVICES'],
};

function findIndexQuote(indices: any[], symbol: string) {
  const aliases = INDEX_SYMBOL_MAP[symbol];
  if (!aliases) return undefined;
  return indices.find(
    (i) =>
      i &&
      (aliases.includes(i.symbol) || aliases.includes(i.name?.toUpperCase())),
  );
}

export function MarketChart({ symbol }: MarketChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const [isClient, setIsClient] = useState(false);
  const [chartInfo, setChartInfo] = useState({ currentPrice: 0, change: 0, changePercent: 0 });
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (!chartContainerRef.current || !isClient) return;

    let chart: any;
    let cancelled = false;

    const initChart = async () => {
      const { createChart } = await import('lightweight-charts');

      if (cancelled) return;

      chart = createChart(chartContainerRef.current!, {
        layout: {
          background: { color: 'transparent' },
          textColor: '#6b7280',
        },
        grid: {
          vertLines: { color: '#e5e7eb' },
          horzLines: { color: '#e5e7eb' },
        },
        width: chartContainerRef.current!.clientWidth,
        height: 300,
        timeScale: {
          timeVisible: true,
          secondsVisible: false,
        },
      });

      chartRef.current = chart;

      const candleSeries = chart.addCandlestickSeries({
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderUpColor: '#22c55e',
        borderDownColor: '#ef4444',
        wickUpColor: '#22c55e',
        wickDownColor: '#ef4444',
      });

      const volumeSeries = chart.addHistogramSeries({
        color: '#3b82f6',
        priceFormat: { type: 'volume' },
        priceScaleId: '',
      });

      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });

      const { candles, volume, currentPrice, change, changePercent, live } =
        await loadChartData(symbol);
      if (cancelled) return;

      candleSeries.setData(candles);
      volumeSeries.setData(volume);

      setChartInfo({ currentPrice, change, changePercent });
      setIsLive(live);

      chart.timeScale().fitContent();

      const handleResize = () => {
        if (chartContainerRef.current && chartRef.current) {
          chartRef.current.applyOptions({
            width: chartContainerRef.current.clientWidth,
          });
        }
      };

      window.addEventListener('resize', handleResize);
    };

    initChart().catch(console.error);

    return () => {
      cancelled = true;
      if (chart) {
        chart.remove();
      }
    };
  }, [symbol, isClient]);

  if (!isClient) {
    return (
      <div className="flex h-[300px] items-center justify-center bg-muted/20 rounded-lg">
        <div className="animate-pulse text-muted-foreground">Loading chart...</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 text-sm">
        <span className="font-semibold text-lg">₹{chartInfo.currentPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        <span className={`font-medium ${chartInfo.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          {chartInfo.change >= 0 ? '+' : ''}{chartInfo.change.toFixed(2)} ({chartInfo.changePercent >= 0 ? '+' : ''}{chartInfo.changePercent.toFixed(2)}%)
        </span>
        <span className="text-xs text-muted-foreground ml-auto">
          5 min | 9:15 AM - 3:30 PM IST
          <span className={`ml-2 ${isLive ? 'text-green-600' : 'text-amber-600'}`}>
            {isLive ? '● Live' : '○ Demo'}
          </span>
        </span>
      </div>
      <div ref={chartContainerRef} className="w-full" />
      <div className="flex items-center justify-end gap-4 text-xs">
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-sm bg-green-500" />
          <span className="text-muted-foreground">Bullish</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-sm bg-red-500" />
          <span className="text-muted-foreground">Bearish</span>
        </div>
      </div>
    </div>
  );
}

// Fetch live OHLC from the backend (/market/ohlc) and a live index quote
// (/market/indices) for the header. Falls back to synthetic intraday candles
// when the backend is unreachable so the chart is never empty.
async function loadChartData(symbol: string): Promise<{
  candles: CandleData[];
  volume: VolumeData[];
  currentPrice: number;
  change: number;
  changePercent: number;
  live: boolean;
}> {
  // Live index quote for the headline numbers (genuinely current via nsetools).
  let liveQuote: any = undefined;
  try {
    const { data: indices } = await marketApi.getIndices();
    if (indices) liveQuote = findIndexQuote(indices, symbol);
  } catch {
    // ignore — fall back to OHLC-derived header
  }

  // Live intraday candles from the backend (yfinance-backed).
  let candles: CandleData[] = [];
  let volume: VolumeData[] = [];
  let live = false;
  try {
    const { data, error } = await marketApi.getOHLC(symbol, '5m');
    if (!error && data && data.length > 0) {
      const seen = new Set<number>();
      for (const c of data) {
        // Backend timestamps are naive UTC; append Z so JS parses as UTC.
        const time = Math.floor(new Date(`${c.timestamp}Z`).getTime() / 1000);
        if (Number.isNaN(time) || seen.has(time)) continue;
        seen.add(time);
        candles.push({ time, open: c.open, high: c.high, low: c.low, close: c.close });
        volume.push({
          time,
          value: c.volume ?? 0,
          color: c.close >= c.open ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)',
        });
      }
      live = candles.length > 0;
    }
  } catch {
    // fall through to synthetic
  }

  if (!live) {
    const mock = generateIntradayData(symbol);
    candles = mock.candles;
    volume = mock.volume;
    return { ...mock, live: false };
  }

  const openPrice = candles[0].open;
  const lastClose = candles[candles.length - 1].close;

  if (liveQuote) {
    return {
      candles,
      volume,
      currentPrice: liveQuote.price ?? lastClose,
      change: liveQuote.change ?? lastClose - openPrice,
      changePercent: liveQuote.change_percent ?? ((lastClose - openPrice) / openPrice) * 100,
      live: true,
    };
  }

  const change = lastClose - openPrice;
  return {
    candles,
    volume,
    currentPrice: lastClose,
    change,
    changePercent: (change / openPrice) * 100,
    live: true,
  };
}

function getIntradayStartTime(): Date {
  const now = new Date();
  const marketOpen = new Date(now);
  marketOpen.setUTCHours(3, 45, 0, 0);

  const day = now.getDay();
  if (day === 0) {
    marketOpen.setDate(marketOpen.getDate() + 1);
  } else if (day === 6) {
    marketOpen.setDate(marketOpen.getDate() + 2);
  }

  return marketOpen;
}

function generateIntradayData(symbol: string) {
  const candles: CandleData[] = [];
  const volume: VolumeData[] = [];

  const basePrice = symbol === 'NIFTY' ? 24500 : 52400;
  const volatility = symbol === 'NIFTY' ? 50 : 100;

  const marketOpen = getIntradayStartTime();
  let currentPrice = basePrice;

  const now = new Date();
  const marketClose = new Date(marketOpen);
  marketClose.setHours(15, 30, 0, 0);

  const endTime = now > marketClose ? marketClose : now;

  let candleTime = new Date(marketOpen);

  while (candleTime <= endTime) {
    const timestamp = Math.floor(candleTime.getTime() / 1000);

    const change = (Math.random() - 0.5) * volatility;
    const open = currentPrice;
    const close = currentPrice + change;
    const high = Math.max(open, close) + Math.random() * (volatility / 2);
    const low = Math.min(open, close) - Math.random() * (volatility / 2);

    candles.push({ time: timestamp, open, high, low, close });

    volume.push({
      time: timestamp,
      value: Math.random() * 1000000 + 500000,
      color: close >= open ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)',
    });

    currentPrice = close;

    candleTime = new Date(candleTime.getTime() + 5 * 60 * 1000);
  }

  const openPrice = candles.length > 0 ? candles[0].open : basePrice;
  const lastClose = candles.length > 0 ? candles[candles.length - 1].close : basePrice;
  const change = lastClose - openPrice;
  const changePercent = (change / openPrice) * 100;

  return { candles, volume, currentPrice: lastClose, change, changePercent };
}
