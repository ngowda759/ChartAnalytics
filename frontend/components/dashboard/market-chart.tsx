'use client';

import { useEffect, useRef, useState } from 'react';

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

export function MarketChart({ symbol }: MarketChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (!chartContainerRef.current || !isClient) return;

    let chart: any;

    const initChart = async () => {
      const { createChart } = await import('lightweight-charts');

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

      const mockData = generateMockData(symbol);
      candleSeries.setData(mockData.candles);
      volumeSeries.setData(mockData.volume);

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

function generateMockData(symbol: string) {
  const candles: CandleData[] = [];
  const volume: VolumeData[] = [];
  
  const basePrice = symbol === 'NIFTY' ? 24500 : 52400;
  const volatility = symbol === 'NIFTY' ? 50 : 100;
  
  const now = new Date();
  let currentPrice = basePrice;
  
  for (let i = 100; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 5 * 60 * 1000);
    const timestamp = Math.floor(time.getTime() / 1000);
    
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
  }
  
  return { candles, volume };
}
