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

// NIFTY closing price at 3:30 PM IST
const NIFTY_CLOSE_PRICE = 24636;
const NIFTY_OPEN_PRICE = 24450; // Approximate open price
const BANKNIFTY_CLOSE_PRICE = 52456;

export function MarketChart({ symbol }: MarketChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const [isClient, setIsClient] = useState(false);
  const [chartInfo, setChartInfo] = useState({ 
    currentPrice: symbol === 'NIFTY' ? NIFTY_CLOSE_PRICE : BANKNIFTY_CLOSE_PRICE, 
    change: symbol === 'NIFTY' ? NIFTY_CLOSE_PRICE - NIFTY_OPEN_PRICE : 0,
    changePercent: symbol === 'NIFTY' ? ((NIFTY_CLOSE_PRICE - NIFTY_OPEN_PRICE) / NIFTY_OPEN_PRICE) * 100 : 0
  });

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

      const mockData = generateIntradayData(symbol);
      candleSeries.setData(mockData.candles);
      volumeSeries.setData(mockData.volume);
      
      setChartInfo({
        currentPrice: mockData.currentPrice,
        change: mockData.change,
        changePercent: mockData.changePercent
      });

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
      <div className="flex items-center gap-4 text-sm">
        <span className="font-semibold text-lg">₹{chartInfo.currentPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        <span className={`font-medium ${chartInfo.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          {chartInfo.change >= 0 ? '+' : ''}{chartInfo.change.toFixed(2)} ({chartInfo.changePercent >= 0 ? '+' : ''}{chartInfo.changePercent.toFixed(2)}%)
        </span>
        <span className="text-xs text-muted-foreground ml-auto">Closed 3:30 PM IST</span>
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

function generateIntradayData(symbol: string) {
  const candles: CandleData[] = [];
  const volume: VolumeData[] = [];
  
  const closePrice = symbol === 'NIFTY' ? NIFTY_CLOSE_PRICE : BANKNIFTY_CLOSE_PRICE;
  const openPrice = symbol === 'NIFTY' ? NIFTY_OPEN_PRICE : closePrice - 200;
  const volatility = symbol === 'NIFTY' ? 30 : 80;
  
  // Market open time (9:15 AM IST = 3:45 UTC)
  const marketOpen = new Date();
  marketOpen.setUTCHours(3, 45, 0, 0);
  
  let currentPrice = openPrice;
  let candleTime = new Date(marketOpen);
  
  // Generate 75 candles (5 min candles from 9:15 to 3:30)
  for (let i = 0; i < 75; i++) {
    const timestamp = Math.floor(candleTime.getTime() / 1000);
    
    // Make the last candle close at the close price
    let targetClose: number;
    if (i === 74) {
      targetClose = closePrice;
    } else {
      const progress = i / 74;
      const priceProgress = (closePrice - openPrice) * progress;
      targetClose = openPrice + priceProgress + (Math.random() - 0.5) * volatility;
    }
    
    const open = currentPrice;
    const close = targetClose;
    const high = Math.max(open, close) + Math.random() * (volatility / 3);
    const low = Math.min(open, close) - Math.random() * (volatility / 3);
    
    candles.push({ time: timestamp, open, high, low, close });
    
    volume.push({
      time: timestamp,
      value: Math.random() * 1000000 + 500000,
      color: close >= open ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)',
    });
    
    currentPrice = close;
    candleTime = new Date(candleTime.getTime() + 5 * 60 * 1000);
  }
  
  const change = closePrice - openPrice;
  const changePercent = (change / openPrice) * 100;
  
  return { candles, volume, currentPrice: closePrice, change, changePercent };
}
