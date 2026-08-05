'use client';

import { useQuery } from '@tanstack/react-query';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn, formatNumber, formatPercentage } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { MarketQuote } from '@/types';

// Mock data - replace with actual API calls
const mockIndices: MarketQuote[] = [
  {
    symbol: 'NIFTY 50',
    name: 'NIFTY 50',
    price: 24567.85,
    change: 123.45,
    changePercent: 0.50,
    open: 24450.00,
    high: 24620.30,
    low: 24420.15,
    previousClose: 24444.40,
    volume: 45678900,
    timestamp: new Date(),
  },
  {
    symbol: 'BANKNIFTY',
    name: 'NIFTY Bank',
    price: 52456.70,
    change: -234.15,
    changePercent: -0.45,
    open: 52680.00,
    high: 52780.25,
    low: 52350.00,
    previousClose: 52690.85,
    volume: 34567890,
    timestamp: new Date(),
  },
  {
    symbol: 'FINNIFTY',
    name: 'NIFTY Fin Services',
    price: 23456.30,
    change: 89.50,
    changePercent: 0.38,
    open: 23380.00,
    high: 23520.40,
    low: 23350.25,
    previousClose: 23366.80,
    volume: 12345678,
    timestamp: new Date(),
  },
  {
    symbol: 'SENSEX',
    name: 'BSE Sensex',
    price: 80789.45,
    change: 456.78,
    changePercent: 0.57,
    open: 80450.00,
    high: 80950.30,
    low: 80350.15,
    previousClose: 80332.67,
    volume: 56789000,
    timestamp: new Date(),
  },
  {
    symbol: 'INDIA VIX',
    name: 'India VIX',
    price: 14.56,
    change: -0.78,
    changePercent: -5.09,
    open: 15.20,
    high: 15.45,
    low: 14.30,
    previousClose: 15.34,
    volume: 8901234,
    timestamp: new Date(),
  },
];

export function MarketIndices() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {mockIndices.map((index) => (
        <IndexCard key={index.symbol} data={index} />
      ))}
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
