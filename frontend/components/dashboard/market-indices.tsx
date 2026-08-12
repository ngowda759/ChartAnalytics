'use client';

import { useQuery } from '@tanstack/react-query';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn, formatNumber, formatPercentage } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { MarketQuote } from '@/types';
import { marketApi } from '@/lib/api';
import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

const REFRESH_INTERVAL_MS = 60_000;

// Backend /market/indices returns snake_case fields; map to the MarketQuote
// shape consumed by the cards.
function toMarketQuote(q: Record<string, unknown>): MarketQuote {
  return {
    symbol: String(q.symbol ?? ''),
    name: String(q.name ?? q.symbol ?? ''),
    price: Number(q.price ?? 0),
    change: Number(q.change ?? 0),
    changePercent: Number(q.change_percent ?? 0),
    open: Number(q.open ?? 0),
    high: Number(q.high ?? 0),
    low: Number(q.low ?? 0),
    previousClose: Number(q.previous_close ?? 0),
    volume: Number(q.volume ?? 0),
    timestamp: q.timestamp ? new Date(String(q.timestamp)) : new Date(),
  };
}

export function MarketIndices() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery<MarketQuote[]>({
    queryKey: ['market-indices'],
    queryFn: async () => {
      const { data, error } = await marketApi.getIndices();
      if (error || !data) {
        throw new Error(error || 'Failed to load indices');
      }
      return data.map(toMarketQuote);
    },
    refetchInterval: REFRESH_INTERVAL_MS,
    refetchOnWindowFocus: false,
  });

  const indices = data ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-end">
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {isLoading && indices.length === 0 ? (
          <p className="col-span-full text-center text-muted-foreground">
            Loading indices...
          </p>
        ) : isError && indices.length === 0 ? (
          <p className="col-span-full text-center text-muted-foreground">
            Unable to load indices. Click Refresh to retry.
          </p>
        ) : (
          indices.map((index) => <IndexCard key={index.symbol} data={index} />)
        )}
      </div>
    </div>
  );
}

function IndexCard({ data }: { data: MarketQuote }) {
  const isPositive = data.change >= 0;
  const isNeutral = data.change === 0;

  return (
    <Card className="relative overflow-hidden">
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">
              {data.name}
            </p>
            <p className="text-2xl font-bold">
              {formatNumber(data.price)}
            </p>
            <div className="flex items-center gap-2">
              <Badge
                variant={isNeutral ? 'neutral' : isPositive ? 'bullish' : 'bearish'}
                className="flex items-center gap-1"
              >
                {isNeutral ? (
                  <Minus className="h-3 w-3" />
                ) : isPositive ? (
                  <TrendingUp className="h-3 w-3" />
                ) : (
                  <TrendingDown className="h-3 w-3" />
                )}
                {formatPercentage(data.changePercent)}
              </Badge>
            </div>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
          <div>
            <p className="text-muted-foreground">High</p>
            <p className="font-medium">{formatNumber(data.high)}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Low</p>
            <p className="font-medium">{formatNumber(data.low)}</p>
          </div>
        </div>

        {/* Price change indicator */}
        <div
          className={cn(
            'absolute bottom-0 left-0 right-0 h-1',
            isNeutral ? 'bg-gray-400' : isPositive ? 'bg-green-500' : 'bg-red-500'
          )}
        />
      </CardContent>
    </Card>
  );
}
