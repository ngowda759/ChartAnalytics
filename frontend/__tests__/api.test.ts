/**
 * Tests for the canonical API base URL resolution in lib/api.ts.
 *
 * The base URL must normalize NEXT_PUBLIC_API_URL in any form (with/without
 * trailing slash, with/without /api/v1) to a single base ending in /api/v1,
 * so callers never hit /api/v1/api/v1 (double prefix) or miss /api/v1.
 */
import { jest } from '@jest/globals';

function loadBaseUrl(): string {
  const mod = require('@/lib/api');
  return (mod as any).__API_BASE_URL as string;
}

describe('getApiBaseUrl normalization', () => {
  const originalEnv = process.env.NEXT_PUBLIC_API_URL;

  afterEach(() => {
    if (originalEnv === undefined) {
      delete process.env.NEXT_PUBLIC_API_URL;
    } else {
      process.env.NEXT_PUBLIC_API_URL = originalEnv;
    }
    jest.resetModules();
  });

  it('appends /api/v1 when the env var has no path', () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
    jest.isolateModules(() => {
      expect(loadBaseUrl()).toBe('http://localhost:8000/api/v1');
    });
  });

  it('does not double-prefix when env var already ends with /api/v1', () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000/api/v1';
    jest.isolateModules(() => {
      expect(loadBaseUrl()).toBe('http://localhost:8000/api/v1');
    });
  });

  it('strips a trailing slash before normalizing', () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000/api/v1/';
    jest.isolateModules(() => {
      expect(loadBaseUrl()).toBe('http://localhost:8000/api/v1');
    });
  });

  it('strips trailing slash on the bare host then appends /api/v1', () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000/';
    jest.isolateModules(() => {
      expect(loadBaseUrl()).toBe('http://localhost:8000/api/v1');
    });
  });
});

describe('ScreenerWidget type carries runtime provenance', () => {
  it('accepts status/source/error fields', () => {
    const mod = require('@/lib/api');
    const widget: mod.ScreenerWidget = {
      id: 'top_gainers',
      title: 'Top Gainers',
      timeframe: 'daily',
      columns: ['symbol'],
      rows: [],
      last_updated: '2026-01-01T00:00:00Z',
      status: 'cached',
      source: 'cache',
      error: null,
    };
    expect(widget.status).toBe('cached');
    expect(widget.source).toBe('cache');
  });
});

