'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';

/**
 * Unified tile state contract. Every major dashboard tile follows this shape
 * so loading / success / cached / fallback / error are handled consistently.
 *
 * `source` is derived from the API payload when the backend tags its data
 * (e.g. "live" | "synthetic_fallback" | "unavailable" | "synthetic"); when the
 * backend has no source field it defaults to "unknown".
 */
export type TileDataSource =
  | 'live'
  | 'cached'
  | 'fallback'
  | 'synthetic'
  | 'unavailable'
  | 'unknown';

export interface TileState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  updatedAt: string | null;
  source: TileDataSource;
  stale: boolean;
  refetch: () => void;
}

/**
 * Map a backend-reported source string onto the canonical TileDataSource enum.
 * Keeps the UI resilient to minor backend wording differences.
 */
export function normalizeSource(raw?: string | null): TileDataSource {
  if (!raw) return 'unknown';
  const v = raw.toLowerCase();
  if (v === 'live') return 'live';
  if (v === 'synthetic_fallback' || v === 'fallback') return 'fallback';
  if (v === 'synthetic') return 'synthetic';
  if (v === 'unavailable') return 'unavailable';
  if (v === 'cached') return 'cached';
  return 'unknown';
}

/**
 * A tile query hook that turns any async data source into a TileState.
 *
 * - Independent per-tile loading/error (each tile gets its own query key).
 * - `refetch()` exposes manual refresh.
 * - `stale` is true when the backend flags `is_stale` OR React Query reports the
 *   data as stale.
 */
export function useTileQuery<TResponse, TData = TResponse>(
  queryKey: readonly unknown[],
  fetcher: () => Promise<{ data: TResponse | null; error?: string }>,
  options?: {
    /** Pull the tile payload out of a backend envelope, if any. */
    select?: (response: TResponse) => {
      data: TData;
      source?: string | null;
      isStale?: boolean;
      updatedAt?: string | null;
    };
    refetchIntervalMs?: number;
    enabled?: boolean;
  }
): TileState<TData> {
  const queryClient = useQueryClient();

  const query = useQuery<TResponse>({
    queryKey,
    queryFn: async () => {
      const res = await fetcher();
      if (res.error || res.data === null) {
        throw new Error(res.error ?? 'Data unavailable');
      }
      return res.data as TResponse;
    },
    refetchInterval: options?.refetchIntervalMs,
    enabled: options?.enabled,
    retry: false,
  });

  const refetch = useCallback(() => {
    void query.refetch();
  }, [query]);

  const state = useMemo<TileState<TData>>(() => {
    const meta = options?.select && query.data ? options.select(query.data) : null;
    const data = meta ? meta.data : ((query.data as unknown) as TData | null);
    const source = normalizeSource(meta?.source ?? null);
    return {
      data: data ?? null,
      loading: query.isLoading,
      error: query.error ? (query.error as Error).message : null,
      updatedAt: meta?.updatedAt ?? (query.dataUpdatedAt ? new Date(query.dataUpdatedAt).toISOString() : null),
      source,
      stale: Boolean(meta?.isStale) || query.isStale,
      refetch,
    };
  }, [query.data, query.isLoading, query.error, query.isStale, query.dataUpdatedAt, options, refetch]);

  // Keep queryClient referenced to avoid dead-code elimination of the import
  // in consumers that rely on cache invalidation helpers.
  void queryClient;
  return state;
}
