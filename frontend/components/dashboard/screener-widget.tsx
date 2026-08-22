'use client';

import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Download, ChevronUp, ChevronDown, ChevronsUpDown, BarChart3 } from 'lucide-react';
import type { ScreenerWidget as ScreenerWidgetType, ScreenerRow } from '@/lib/api';
import { cn, formatVolume, formatISTTime } from '@/lib/utils';

type SortDir = 'asc' | 'desc' | null;

interface ColumnMeta {
  key: string;
  label: string;
  numeric: boolean;
  accessor: (row: ScreenerRow) => number | string | null | undefined;
  formatter?: (val: number | string | null) => string;
}

const COLUMN_LABELS: Record<string, string> = {
  symbol: 'Symbol',
  change_percent: '% Chg',
  ltp: 'Ltp',
  volume: 'Volume',
  'extra.volume_factor': 'V Fac',
  'extra.vwap': 'VWAP',
  'extra.rsi': 'RSI',
  'extra.pct_from_high': '% High',
  'extra.prediction_direction': 'Forecast',
  'extra.predicted_change_pct': 'Pred %',
  'extra.prediction_conviction': 'Conviction',
  'extra.prediction_target': 'Target',
};

// Extra fields that hold string metadata (not numeric metrics) — rendered
// verbatim instead of being coerced to a number.
const STRING_EXTRA_FIELDS = new Set(['prediction_direction']);

function getExtra(row: ScreenerRow, dotted: string): number | string | null {
  const [, field] = dotted.split('extra.');
  const raw = row.extra?.[field];
  if (raw === null || raw === undefined) return null;
  if (STRING_EXTRA_FIELDS.has(field)) return String(raw);
  // `extra` mixes numeric metrics and string metadata (e.g. source); only
  // expose numeric values to the numeric accessor.
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

function buildColumns(keys: string[]): ColumnMeta[] {
  return keys.map((key) => {
    const isExtra = key.startsWith('extra.');
    let accessor: (row: ScreenerRow) => number | string | null | undefined;
    switch (key) {
      case 'symbol':
        accessor = (r) => r.symbol;
        break;
      case 'change_percent':
        accessor = (r) => r.change_percent;
        break;
      case 'ltp':
        accessor = (r) => r.ltp;
        break;
      case 'volume':
        accessor = (r) => r.volume;
        break;
      default:
        accessor = (r) => (isExtra ? getExtra(r, key) : null);
    }
    return {
      key,
      label: COLUMN_LABELS[key] ?? key,
      numeric: key !== 'symbol',
      accessor,
    };
  });
}

function formatValue(col: ColumnMeta, val: number | string | null | undefined): string {
  if (val === null || val === undefined) return '-';
  if (col.key === 'symbol') return String(val);
  if (col.key === 'extra.prediction_direction') return String(val);
  const n = Number(val);
  if (!Number.isFinite(n)) return String(val);
  if (col.key === 'change_percent' || col.key === 'extra.predicted_change_pct') {
    return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
  }
  if (col.key === 'volume') return formatVolume(n);
  if (col.key === 'ltp' || col.key === 'extra.vwap' || col.key === 'extra.prediction_target') {
    return n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (col.key === 'extra.rsi' || col.key === 'extra.volume_factor' || col.key === 'extra.pct_from_high') {
    return n.toFixed(2);
  }
  return String(n);
}

function exportCsv(widget: ScreenerWidgetType) {
  const cols = buildColumns(widget.columns);
  const header = cols.map((c) => c.label).join(',');
  const lines = widget.rows.map((row) =>
    cols.map((c) => formatValue(c, c.accessor(row))).join(',')
  );
  const csv = [header, ...lines].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${widget.id}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

interface Props {
  widget: ScreenerWidgetType;
  showChartPreview: boolean;
}

export function ScreenerWidget({ widget, showChartPreview }: Props) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);

  const columns = useMemo(() => buildColumns(widget.columns), [widget.columns]);

  const sortedRows = useMemo(() => {
    if (!sortKey || !sortDir) return widget.rows;
    const col = columns.find((c) => c.key === sortKey);
    if (!col) return widget.rows;
    const dir = sortDir === 'asc' ? 1 : -1;
    return [...widget.rows].sort((a, b) => {
      const av = col.accessor(a);
      const bv = col.accessor(b);
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;
      if (typeof av === 'string' || typeof bv === 'string') {
        return String(av).localeCompare(String(bv)) * dir;
      }
      return (Number(av) - Number(bv)) * dir;
    });
  }, [widget.rows, sortKey, sortDir, columns]);

  const toggleSort = (key: string) => {
    if (sortKey !== key) {
      setSortKey(key);
      setSortDir('desc');
    } else if (sortDir === 'desc') {
      setSortDir('asc');
    } else if (sortDir === 'asc') {
      setSortKey(null);
      setSortDir(null);
    }
  };

  const updated = formatISTTime(widget.last_updated);

  // Per-widget provenance from the runtime repair. Maps the backend status/source
  // to a labelled badge so a cached/fallback/unavailable tile is never silent.
  const statusBadge = (() => {
    const s = widget.status;
    if (!s || s === 'live') return null;
    const map: Record<string, { label: string; className: string }> = {
      cached: { label: 'Cached', className: 'border-amber-500/40 text-amber-600' },
      fallback: { label: 'Fallback', className: 'border-yellow-500/40 text-yellow-600' },
      unavailable: { label: 'Unavailable', className: 'border-red-500/40 text-red-600' },
      error: { label: 'Error', className: 'border-red-500/40 text-red-600' },
      mock: { label: 'Mock', className: 'border-slate-500/40 text-slate-500' },
    };
    const entry = map[s];
    if (!entry) return null;
    return (
      <Badge variant="outline" className={`text-xs font-normal ${entry.className}`}>
        {entry.label}
      </Badge>
    );
  })();

  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              {widget.title}
              <Badge variant="outline" className="text-xs font-normal">
                {widget.timeframe}
              </Badge>
              {statusBadge}
            </CardTitle>
            {widget.description && (
              <p className="text-xs text-muted-foreground mt-1">{widget.description}</p>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => exportCsv(widget)}
            title="Export CSV"
          >
            <Download className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex-1">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className={cn(
                      'px-2 py-1.5 text-xs font-medium text-muted-foreground',
                      col.numeric ? 'text-right' : 'text-left'
                    )}
                  >
                    <button
                      onClick={() => toggleSort(col.key)}
                      className={cn(
                        'inline-flex items-center gap-1 hover:text-foreground',
                        col.numeric && 'flex-row-reverse'
                      )}
                    >
                      {col.label}
                      {sortKey === col.key ? (
                        sortDir === 'asc' ? (
                          <ChevronUp className="h-3 w-3" />
                        ) : (
                          <ChevronDown className="h-3 w-3" />
                        )
                      ) : (
                        <ChevronsUpDown className="h-3 w-3 opacity-40" />
                      )}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedRows.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} className="px-2 py-6 text-center text-muted-foreground">
                    No data for table
                  </td>
                </tr>
              ) : (
                sortedRows.map((row) => (
                  <tr key={row.symbol} className="border-b last:border-0 hover:bg-muted/40">
                    {columns.map((col) => {
                      const val = col.accessor(row);
                      const formatted = formatValue(col, val);
                      const numVal = typeof val === 'number' ? val : Number(val);
                      const isPositive = col.key === 'change_percent' && numVal > 0;
                      const isNegative = col.key === 'change_percent' && numVal < 0;
                      return (
                        <td
                          key={col.key}
                          className={cn(
                            'px-2 py-1.5',
                            col.numeric ? 'text-right tabular-nums' : 'text-left'
                          )}
                        >
                          {col.key === 'symbol' ? (
                            <span className="font-medium text-primary">{formatted}</span>
                          ) : (
                            <span
                              className={cn(
                                isPositive && 'text-green-600',
                                isNegative && 'text-red-600'
                              )}
                            >
                              {formatted}
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {showChartPreview && sortedRows.length > 0 && (
          <div className="mt-3 flex items-end gap-1 h-16">
            {sortedRows.slice(0, 20).map((row, i) => {
              const pct = row.change_percent ?? 0;
              const height = Math.min(100, Math.abs(pct) * 12 + 8);
              return (
                <div
                  key={`${row.symbol}-${i}`}
                  className={cn(
                    'flex-1 rounded-sm',
                    pct >= 0 ? 'bg-green-500/70' : 'bg-red-500/70'
                  )}
                  style={{ height: `${height}%` }}
                  title={`${row.symbol}: ${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`}
                />
              );
            })}
          </div>
        )}
      </CardContent>
      <div className="px-6 pb-3 text-xs text-muted-foreground flex items-center gap-1">
        <BarChart3 className="h-3 w-3" />
        Updated {updated} IST · {sortedRows.length} rows
      </div>
    </Card>
  );
}
