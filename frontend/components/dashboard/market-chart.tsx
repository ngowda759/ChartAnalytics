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

// Convert local time to IST
function toIST(localDate: Date): Date {
  // IST is UTC+5:30
  const istOffset = 5.5 * 60 * 60 * 1000;
  const utcTime = localDate.getTime() + (localDate.getTimezoneOffset() * 60 * 1000);
  return new Date(utcTime + istOffset);
}

// Get the last trading day (handles weekends and holidays)
function getLastTradingDay(): Date {
  const now = new Date();
  const ist = toIST(now);
  let day = ist.getDay();
  
  // If it's Saturday (6), go back to Friday
  // If it's Sunday (0), go back to Friday
  // If it's Monday (1), check if it's before market hours - go back to Friday
  if (day === 0) { // Sunday
    ist.setDate(ist.getDate() - 2); // Go to Friday
  } else if (day === 6) { // Saturday
    ist.setDate(ist.getDate() - 1); // Go to Friday
  }
  
  return ist;
}

// Generate intraday timestamps for NSE market hours (9:15 AM - 3:30 PM IST)
function getIntradayStartTime(): Date {
  const tradingDay = getLastTradingDay();
  
  // Set to market open time 9:15 AM IST
  tradingDay.setHours(9, 15, 0, 0);
  
  return tradingDay;
}

function isWithinMarketHours(date: Date): boolean {
  // IST market hours: 9:15 AM to 3:30 PM
  const hours = date.getHours();
  const minutes = date.getMinutes();
  const totalMinutes = hours * 60 + minutes;
  
  // 9:15 = 555, 15:30 = 930
  return totalMinutes >= 555 && totalMinutes <= 930;
}

export function MarketChart({ symbol }: MarketChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const [isClient, setIsClient] = useState(false);
  const [chartInfo, setChartInfo] = useState({ currentPrice: 0, change: 0, changePercent: 0 });

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
        <span className="text-xs text-muted-foreground ml-auto">5 min | 9:15 AM - 3:30 PM IST</span>
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
  
  const basePrice = symbol === 'NIFTY' ? 24500 : 52400;
  const volatility = symbol === 'NIFTY' ? 50 : 100;
  
  // Get start time for market open in IST
  const marketOpen = getIntradayStartTime();
  let currentPrice = basePrice;
  
  // Get current time in IST
  const nowIST = toIST(new Date());
  const marketClose = new Date(marketOpen);
  marketClose.setHours(15, 30, 0, 0); // 3:30 PM IST
  
  // If current time is after market close, show full session
  // Otherwise show candles up to current time
  const endTime = nowIST > marketClose ? marketClose : nowIST;
  
  // Generate 5-minute candles from market open
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
    
    // Move to next 5-minute candle
    candleTime = new Date(candleTime.getTime() + 5 * 60 * 1000);
  }
  
  // Calculate overall change from open
  const openPrice = candles.length > 0 ? candles[0].open : basePrice;
  const lastClose = candles.length > 0 ? candles[candles.length - 1].close : basePrice;
  const change = lastClose - openPrice;
  const changePercent = (change / openPrice) * 100;
  
  return { candles, volume, currentPrice: lastClose, change, changePercent };
}
