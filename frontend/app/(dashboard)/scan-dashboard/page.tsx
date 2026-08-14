'use client';

import { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, Copy, Check, BarChart3, LineChart, Clock } from 'lucide-react';
import { scannerApi, type ScreenerDashboard as ScreenerDashboardType } from '@/lib/api';
import { ScreenerWidget } from '@/components/dashboard/screener-widget';
import { toast } from 'sonner';

const DEFAULT_DASHBOARD_ID = 'nse-system';
const REFRESH_INTERVAL_MS = 60_000;

interface DashboardResult {
  dashboard: ScreenerDashboardType;
  source?: string;
  warnings?: string[];
}

export default function ScanDashboardPage() {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showChartPreview, setShowChartPreview] = useState(false);
  const [copied, setCopied] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchDashboard = useCallback(async (): Promise<DashboardResult> => {
    const { data, error, source, warnings } = await scannerApi.getNseDashboard();
    if (error || !data) {
      throw new Error(error || 'Failed to load dashboard');
    }
    return { dashboard: data, source, warnings };
  }, []);

  const { data, isLoading, isError, refetch, isFetching } = useQuery<DashboardResult>({
    queryKey: ['scan-dashboard', DEFAULT_DASHBOARD_ID],
    queryFn: fetchDashboard,
    refetchInterval: autoRefresh ? REFRESH_INTERVAL_MS : false,
    refetchOnWindowFocus: false,
  });

  const dashboard = data?.dashboard;
  const isFallback = data?.source && data.source !== 'live';

  useEffect(() => {
    if (data) setLastUpdated(new Date());
  }, [data]);

  const handleCopy = async () => {
    if (!dashboard) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(dashboard, null, 2));
      setCopied(true);
      toast.success('Dashboard JSON copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy dashboard');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">
              {dashboard?.name ?? 'System'}
            </h1>
            <Badge variant="outline">by {dashboard?.author ?? 'ChartAnalytics'}</Badge>
            {isFallback && (
              <Badge variant="outline" className="border-yellow-500/40 text-yellow-600">
                Fallback data
              </Badge>
            )}
          </div>
          <p className="mt-1 text-muted-foreground">
            {dashboard?.description ??
              'Multi-widget market scan dashboard (Chartink-style) with live NSE data'}
          </p>
          {isFallback && data?.warnings && data.warnings.length > 0 && (
            <p className="mt-1 text-xs text-yellow-600">
              {data.warnings.join('; ')}
            </p>
          )}
          {lastUpdated && (
            <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              Last updated {lastUpdated.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })} IST
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant={autoRefresh ? 'default' : 'outline'}
            size="sm"
            onClick={() => setAutoRefresh((v) => !v)}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${autoRefresh || isFetching ? 'animate-spin' : ''}`} />
            Auto refresh {autoRefresh ? 'on' : 'off'}
          </Button>
          <Button
            variant={showChartPreview ? 'default' : 'outline'}
            size="sm"
            onClick={() => setShowChartPreview((v) => !v)}
          >
            {showChartPreview ? <LineChart className="h-4 w-4 mr-2" /> : <BarChart3 className="h-4 w-4 mr-2" />}
            Chart preview
          </Button>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={handleCopy}>
            {copied ? <Check className="h-4 w-4 mr-2" /> : <Copy className="h-4 w-4 mr-2" />}
            Copy dashboard
          </Button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && !dashboard && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i} className="h-64 animate-pulse bg-muted/40" />
          ))}
        </div>
      )}

      {isError && !dashboard && (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            Unable to load the scan dashboard. The NSE data source may be unavailable
            (e.g. outside market hours). Click Refresh to retry.
          </CardContent>
        </Card>
      )}

      {/* Widgets grid */}
      {dashboard && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {dashboard.widgets.map((widget) => (
            <ScreenerWidget
              key={widget.id}
              widget={widget}
              showChartPreview={showChartPreview}
            />
          ))}
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Live NSE data via nsetools · Chartink-style formula screeners (NR7 breakout,
        potential breakouts) · For educational purposes only
      </p>
    </div>
  );
}
