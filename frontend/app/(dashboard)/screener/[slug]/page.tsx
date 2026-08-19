'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, Clock } from 'lucide-react';
import { scannerApi } from '@/lib/api';
import { formatISTTime } from '@/lib/utils';
import { ScreenerWidget } from '@/components/dashboard/screener-widget';

const SCREENER_META: Record<string, { title: string; description: string }> = {
  'copy-morning-scanner-for-buy-nr7-based-breakout-8': {
    title: 'Morning Scanner - NR7 Breakout (Buy)',
    description:
      'NR7 (narrowest 7-day range) with weekly + monthly uptrend, SMA 20>40>60 stack and volume surge > 1.25x',
  },
  'potential-breakouts': {
    title: 'Potential Breakouts',
    description:
      'Close within 5% of 200-day high after a consolidation, with volume above its 50-day average',
  },
};

export default function ScreenerDetailPage() {
  const params = useParams<{ slug: string }>();
  const slug = decodeURIComponent(params.slug);
  const [showChartPreview, setShowChartPreview] = useState(false);
  const meta = SCREENER_META[slug] ?? { title: slug, description: 'Chartink-style screener' };

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['screener', slug],
    queryFn: async () => {
      const { data, error } = await scannerApi.runScreener(slug);
      if (error || !data) throw new Error(error || 'Failed to run screener');
      return data;
    },
    refetchOnWindowFocus: false,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">{meta.title}</h1>
            <Badge variant="outline">{data?.timeframe ?? 'daily'}</Badge>
          </div>
          <p className="mt-1 text-muted-foreground">{meta.description}</p>
          <p className="mt-1 text-xs text-muted-foreground">Screener slug: <code>{slug}</code></p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant={showChartPreview ? 'default' : 'outline'}
            size="sm"
            onClick={() => setShowChartPreview((v) => !v)}
          >
            Chart preview
          </Button>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Re-run scan
          </Button>
        </div>
      </div>

      {isLoading && !data && (
        <Card>
          <CardContent className="flex h-64 items-center justify-center">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          </CardContent>
        </Card>
      )}

      {isError && !data && (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            Unable to run this screener. Click Re-run scan to retry.
          </CardContent>
        </Card>
      )}

      {data && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          {data.rows.length} stocks match · updated{' '}
          {formatISTTime(data.last_updated)} IST
        </div>
      )}

      {data && <ScreenerWidget widget={data} showChartPreview={showChartPreview} />}
    </div>
  );
}
