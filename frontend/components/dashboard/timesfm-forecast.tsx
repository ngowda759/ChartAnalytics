'use client';

import { useEffect, useRef, useState } from 'react';
import { timesfmApi, type TimesFMForecast } from '@/lib/api';

interface TimesFMForecastProps {
  symbol: string;
}

function toChartTime(value: string): number {
  return Math.floor(new Date(`${value.slice(0, 10)}T00:00:00Z`).getTime() / 1000);
}

export function TimesFMForecastPanel({ symbol }: TimesFMForecastProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [forecast, setForecast] = useState<TimesFMForecast | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setForecast(null);
    setError(null);
  }, [symbol]);

  const loadForecast = async (refresh = false) => {
    setLoading(true);
    setError(null);
    const result = await timesfmApi.forecast(symbol, 10, refresh);
    if (result.error || !result.data) {
      setError(result.error || 'TimesFM forecast is unavailable.');
      setForecast(null);
    } else {
      setForecast(result.data);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (!forecast || !containerRef.current) return;
    let chart: any;
    let cancelled = false;
    const render = async () => {
      const { createChart } = await import('lightweight-charts');
      if (cancelled || !containerRef.current) return;
      chart = createChart(containerRef.current, {
        width: containerRef.current.clientWidth,
        height: 220,
        layout: { background: { color: 'transparent' }, textColor: '#6b7280' },
        grid: {
          vertLines: { color: '#e5e7eb' },
          horzLines: { color: '#e5e7eb' },
        },
        rightPriceScale: { borderVisible: false },
        timeScale: { borderVisible: false, timeVisible: false },
      });
      const anchor = {
        time: toChartTime(forecast.last_observation.timestamp) as any,
        value: forecast.last_observation.close,
      };
      const median = chart.addLineSeries({
        color: '#2563eb',
        lineWidth: 3,
        title: 'P50 median',
      });
      const lower = chart.addLineSeries({
        color: '#94a3b8',
        lineWidth: 1,
        lineStyle: 2,
        title: 'P10',
      });
      const upper = chart.addLineSeries({
        color: '#94a3b8',
        lineWidth: 1,
        lineStyle: 2,
        title: 'P90',
      });
      median.setData([
        anchor,
        ...forecast.forecast.map((p) => ({
          time: toChartTime(p.timestamp) as any,
          value: p.median,
        })),
      ]);
      lower.setData([
        anchor,
        ...forecast.forecast.map((p) => ({
          time: toChartTime(p.timestamp) as any,
          value: p.lower,
        })),
      ]);
      upper.setData([
        anchor,
        ...forecast.forecast.map((p) => ({
          time: toChartTime(p.timestamp) as any,
          value: p.upper,
        })),
      ]);
      chart.timeScale().fitContent();
    };
    render().catch(() => setError('Unable to render the TimesFM forecast chart.'));
    const resize = () => {
      if (chart && containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', resize);
    return () => {
      cancelled = true;
      window.removeEventListener('resize', resize);
      chart?.remove();
    };
  }, [forecast]);

  return (
    <section className="rounded-lg border bg-card p-4 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold">TimesFM AI forecast</h3>
          <p className="text-xs text-muted-foreground">
            Daily closing-price forecast · 10 steps · P10 / P50 / P90
          </p>
        </div>
        <button
          type="button"
          onClick={() => loadForecast(Boolean(forecast))}
          disabled={loading}
          className="rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50"
        >
          {loading ? 'Generating…' : forecast ? 'Refresh forecast' : 'Generate forecast'}
        </button>
      </div>
      {error && <p role="alert" className="text-sm text-amber-700">{error}</p>}
      {forecast && (
        <>
          <div ref={containerRef} className="w-full" />
          <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
            <span><span className="text-blue-600">━</span> P50 median</span>
            <span><span className="text-slate-400">╌</span> P10 / P90 interval</span>
            <span>Data: {forecast.source}</span>
            <span>{forecast.historical_points} daily observations</span>
          </div>
          <p className="text-xs text-muted-foreground">{forecast.disclaimer}</p>
        </>
      )}
      {!forecast && !error && !loading && (
        <p className="text-sm text-muted-foreground">
          Forecasting is optional and may be disabled on this deployment. Generate
          a forecast to load the TimesFM 2.5 model.
        </p>
      )}
    </section>
  );
}
