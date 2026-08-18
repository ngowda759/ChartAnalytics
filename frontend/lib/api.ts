// API Client for ChartAnalytics Backend

/**
 * Resolve the canonical API base URL.
 *
 * Accepts NEXT_PUBLIC_API_URL in any of these forms and normalizes to a base
 * ending in `/api/v1` (no trailing slash):
 *   - http://localhost:8000
 *   - http://localhost:8000/
 *   - http://localhost:8000/api/v1
 *   - http://localhost:8000/api/v1/
 *
 * This prevents both `/api/v1/api/v1` (double prefix) and missing `/api/v1`.
 */
const getApiBaseUrl = (): string => {
  const raw = process.env.NEXT_PUBLIC_API_URL;
  if (raw) {
    // Strip trailing slashes, then ensure it ends with /api/v1 exactly once.
    let url = raw.replace(/\/+$/, '');
    if (!url.endsWith('/api/v1')) {
      url = `${url}/api/v1`;
    }
    return url;
  }
  // Relative URL for browser (works with Next.js API proxy).
  if (typeof window !== 'undefined') {
    return '/api/v1';
  }
  // Server-side SSR fallback.
  return 'http://localhost:8000/api/v1';
};

const API_BASE_URL = getApiBaseUrl();

/** Test-only export of the resolved base URL (not for production use). */
export const __API_BASE_URL = API_BASE_URL;

interface ApiResponse<T> {
  data: T;
  error?: string;
}

export interface ScreenerRow {
  symbol: string;
  name?: string | null;
  ltp?: number | null;
  change_percent?: number | null;
  volume?: number | null;
  // `extra` carries both numeric metrics and string metadata such as
  // `source: "synthetic_fallback"`, so it must accept mixed value types.
  extra?: Record<string, unknown> | null;
}

export interface ScreenerWidget {
  id: string;
  title: string;
  description?: string | null;
  timeframe: string;
  columns: string[];
  rows: ScreenerRow[];
  last_updated: string;
  // Per-widget provenance added by the runtime repair: lets the UI render
  // live / cached / fallback / unavailable distinctly.
  status?: 'live' | 'cached' | 'fallback' | 'unavailable' | 'error';
  source?: 'nse' | 'broker' | 'cache' | 'synthetic' | 'none';
  error?: string | null;
}

export interface ScreenerDashboard {
  id: string;
  name: string;
  author: string;
  description?: string | null;
  widgets: ScreenerWidget[];
}

/** Envelope returned by /api/v1/scanner/nse-dashboard. */
export interface ScreenerDashboardResponse {
  success: boolean;
  source: 'live' | 'cached' | 'synthetic_fallback' | 'unknown';
  data: ScreenerDashboard;
  warnings: string[];
  generated_at?: string;
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      return {
        data: null as T,
        error: `HTTP error! status: ${response.status}`,
      };
    }

    const data = await response.json();
    return { data };
  } catch (error) {
    return {
      data: null as T,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

// Market Data API
export interface MarketQuote {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
  open: number;
  high: number;
  low: number;
  previous_close: number;
  volume: number;
  timestamp: string;
}

export interface MarketStats {
  advances: number | null;
  declines: number | null;
  unchanged: number | null;
  india_vix: number | null;
  india_vix_change_percent: number | null;
  nifty_pcr: number | null;
  source: 'live' | 'unavailable' | 'unknown';
  timestamp: string;
  is_stale: boolean;
}

export interface OHLCResponse {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export const marketApi = {
  getQuotes: (symbols?: string[]) => {
    const list = symbols && symbols.length ? symbols.join(',') : '';
    return fetchApi<MarketQuote[]>(
      `/market/quotes${list ? `?symbols=${encodeURIComponent(list)}` : ''}`
    );
  },
  // Indices are mapped to a camelCase MarketQuote by the consuming component;
  // keep the raw snake_case backend shape here.
  getIndices: () => fetchApi<Record<string, unknown>[]>('/market/indices'),
  getOHLC: (symbol: string, timeframe: string) =>
    fetchApi<OHLCResponse[]>(`/market/ohlc/${symbol}?interval=${timeframe}`),
  getStats: () => fetchApi<MarketStats>('/market/stats'),
};

// Option Chain API
export interface OptionAnalysis {
  symbol: string;
  spot_price: number;
  expiry_date: string;
  key_metrics: {
    pcr: number;
    pcr_change: number;
    max_pain: number;
    atm_iv: number;
    iv_skew: number;
  };
  oi_summary: {
    total_call_oi: number;
    total_put_oi: number;
    net_oi: number;
  };
  outlook: {
    trend: string;
    confidence: number;
    interpretation: string;
  };
  support_levels: number[];
  resistance_levels: number[];
  source: 'live' | 'synthetic';
}

export const optionsApi = {
  getChain: (symbol: string) => fetchApi<unknown>(`/options/chain/${symbol}`),
  getPCR: (symbol: string) => fetchApi<unknown>(`/options/pcr/${symbol}`),
  getMaxPain: (symbol: string) => fetchApi<unknown>(`/options/max-pain/${symbol}`),
  getAnalysis: (symbol: string, expiry?: string) => {
    const query = expiry ? `?expiry=${expiry}` : '';
    return fetchApi<OptionAnalysis>(
      `/options/analysis/${encodeURIComponent(symbol)}${query}`
    );
  },
};

// Indicators API
export const indicatorsApi = {
  getIndicators: (symbol: string) =>
    fetchApi<any>(`/indicators/all/${symbol}`),
  getEMA: (symbol: string) => fetchApi<any>(`/indicators/ema/${symbol}`),
  getRSI: (symbol: string) => fetchApi<any>(`/indicators/rsi/${symbol}`),
  getMACD: (symbol: string) => fetchApi<any>(`/indicators/macd/${symbol}`),
  getVWAP: (symbol: string) => fetchApi<any>(`/indicators/vwap/${symbol}`),
  getSupertrend: (symbol: string) => fetchApi<any>(`/indicators/supertrend/${symbol}`),
  getBollingerBands: (symbol: string) =>
    fetchApi<any>(`/indicators/bollinger/${symbol}`),
  getATR: (symbol: string) => fetchApi<any>(`/indicators/atr/${symbol}`),
  getADX: (symbol: string) => fetchApi<any>(`/indicators/adx/${symbol}`),
};

// Journal API
export const journalApi = {
  getTrades: (limit = 50) => fetchApi<any[]>(`/journal/?limit=${limit}`),
  getTrade: (tradeId: string) => fetchApi<any>(`/journal/${tradeId}`),
  createTrade: (trade: any) =>
    fetchApi<any>('/journal/', { method: 'POST', body: JSON.stringify(trade) }),
  updateTrade: (tradeId: string, updates: any) =>
    fetchApi<any>(`/journal/${tradeId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    }),
  getPerformance: () => fetchApi<any>('/journal/metrics/performance'),
};

// Risk API
export const riskApi = {
  calculatePositionSize: (params: {
    accountSize: number;
    riskPercent: number;
    entryPrice: number;
    stopLoss: number;
    instrument: string;
  }) =>
    fetchApi<any>('/risk/position-size', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
  calculateRisk: (params: {
    entryPrice: number;
    stopLoss: number;
    target: number;
    quantity: number;
    tradeType: string;
  }) =>
    fetchApi<any>('/risk/risk-calculation', {
      method: 'GET',
    }),
  getDailyLimit: () => fetchApi<any>('/risk/daily-limit'),
};

// AI API
export const aiApi = {
  getInsights: (symbol: string) => fetchApi<any>(`/ai/insights/${symbol}`),
  getAllInsights: (limit = 10) => fetchApi<any[]>(`/ai/insights?limit=${limit}`),
  reviewTrade: (params: {
    tradeId: string;
    entryPrice: number;
    exitPrice?: number;
    stopLoss: number;
    target: number;
    quantity: number;
    tradeType: string;
    strategy: string;
    pnl?: number;
    holdingPeriodMinutes?: number;
  }) =>
    fetchApi<any>('/ai/review-trade', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
  analyzePatterns: (params: {
    symbol: string;
    highs: number[];
    lows: number[];
    closes: number[];
    volumes: number[];
    timestamps: string[];
  }) =>
    fetchApi<any>('/ai/analyze-patterns', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
  chat: (message: { role: string; content: string }) =>
    fetchApi<any>('/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
};

// Scanner API
export const scannerApi = {
  getScanResults: () => fetchApi<unknown[]>('/scanner/'),
  getBreakouts: () => fetchApi<unknown[]>('/scanner/breakouts'),
  getOIBuildups: () => fetchApi<unknown[]>('/scanner/oi-buildup'),
  getDashboard: (dashboardId: string) =>
    fetchApi<ScreenerDashboard>(`/scanner/dashboard/${dashboardId}`),
  // The backend returns a {success, source, data, warnings} envelope. Unwrap it
  // so callers receive the ScreenerDashboard while preserving source/warnings.
  getNseDashboard: async (): Promise<
    ApiResponse<ScreenerDashboard | null> & {
      source?: string;
      warnings?: string[];
      generated_at?: string;
    }
  > => {
    const res = await fetchApi<ScreenerDashboardResponse>(
      '/scanner/nse-dashboard'
    );
    if (res.error || !res.data) {
      return { data: null, error: res.error ?? 'No dashboard data' };
    }
    return {
      data: res.data.data,
      source: res.data.source,
      warnings: res.data.warnings,
      generated_at: res.data.generated_at,
    };
  },
  getScreenerSlugs: () => fetchApi<string[]>('/scanner/screeners'),
  runScreener: (slug: string, limit = 25) =>
    fetchApi<ScreenerWidget>(`/scanner/screener/${encodeURIComponent(slug)}?limit=${limit}`),
};

// Alerts API
export const alertsApi = {
  getAlerts: (isActive?: boolean) => {
    const params = isActive !== undefined ? `?is_active=${isActive}` : '';
    return fetchApi<any[]>(`/alerts/${params}`);
  },
  createAlert: (alert: any) =>
    fetchApi<any>('/alerts/', { method: 'POST', body: JSON.stringify(alert) }),
  updateAlert: (alertId: string, updates: any) =>
    fetchApi<any>(`/alerts/${alertId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    }),
  deleteAlert: (alertId: string) =>
    fetchApi<any>(`/alerts/${alertId}`, { method: 'DELETE' }),
  getNotifications: () => fetchApi<any[]>('/alerts/notifications'),
};

// Strategy API
export const strategiesApi = {
  getStrategies: () => fetchApi<any[]>('/strategies/'),
  getStrategy: (strategyId: string) =>
    fetchApi<any>(`/strategies/${strategyId}`),
  createStrategy: (strategy: any) =>
    fetchApi<any>('/strategies/', { method: 'POST', body: JSON.stringify(strategy) }),
  updateStrategy: (strategyId: string, updates: any) =>
    fetchApi<any>(`/strategies/${strategyId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    }),
  backtest: (strategyId: string, params: any) =>
    fetchApi<any>(`/strategies/${strategyId}/backtest`, {
      method: 'POST',
      body: JSON.stringify(params),
    }),
};

// Decision Signals API
export type DecisionAction = 'buy' | 'hold' | 'avoid';

export interface DecisionSignal {
  id: string;
  symbol: string;
  name?: string | null;
  strategy: string;
  display_name: string;
  category: string;
  action: DecisionAction;
  score: number;
  confidence: number;
  entry?: number | null;
  stop_loss?: number | null;
  target?: number | null;
  horizon: string;
  risk_reward?: number | null;
  reasons: string[];
  status: string;
  timestamp: string;
}

export interface DecisionSignalListResponse {
  total: number;
  buy_count: number;
  hold_count: number;
  avoid_count: number;
  signals: DecisionSignal[];
  generated_at: string;
  data_timestamp?: string | null;
  source: string;
  is_stale: boolean;
}

export const decisionSignalsApi = {
  listSignals: (params?: {
    action?: DecisionAction;
    strategy?: string;
    min_score?: number;
    limit?: number;
    refresh?: boolean;
  }) => {
    const qs = new URLSearchParams();
    if (params?.action) qs.set('action', params.action);
    if (params?.strategy) qs.set('strategy', params.strategy);
    if (params?.min_score !== undefined)
      qs.set('min_score', String(params.min_score));
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.refresh) qs.set('refresh', 'true');
    const query = qs.toString();
    return fetchApi<DecisionSignalListResponse>(
      `/decision-signals/signals${query ? `?${query}` : ''}`
    );
  },
  getStrategies: () => fetchApi<string[]>('/decision-signals/strategies'),
  getSignal: (signalId: string) =>
    fetchApi<DecisionSignal>(`/decision-signals/signals/${encodeURIComponent(signalId)}`),
};

// Agent Analysis API (TradingAgents-style pipeline)
export interface AgentAnalysisListResponse {
  total: number;
  buy_count: number;
  sell_count: number;
  hold_count: number;
  results: Record<string, unknown>[];
  generated_at: string;
  data_timestamp?: string | null;
  source: string;
  is_stale: boolean;
}

export const agentAnalysisApi = {
  list: (limit = 25, refresh = false) =>
    fetchApi<AgentAnalysisListResponse>(
      `/agent-analysis/?limit=${limit}${refresh ? '&refresh=true' : ''}`
    ),
  get: (symbol: string, refresh = false) =>
    fetchApi<Record<string, unknown>>(
      `/agent-analysis/${encodeURIComponent(symbol)}${refresh ? '?refresh=true' : ''}`
    ),
};

// ---------------------------------------------------------------------------
// System / market-data provider status
// ---------------------------------------------------------------------------

export interface MarketDataStatus {
  status: 'live' | 'cached' | 'unavailable' | 'mock' | string;
  provider: string;
  label: string;
  connected: boolean;
  last_success?: string | null;
  error?: string | null;
}

export interface DataProviderStatus {
  provider: string;
  configured: boolean;
  connected: boolean;
  quote: boolean;
  historical_ohlcv: boolean;
  options: boolean;
  last_success?: string | null;
  error?: string | null;
}

export const systemApi = {
  marketStatus: async () => (await fetchApi<MarketDataStatus>('/market/status')).data,
  dataProvider: async () =>
    (await fetchApi<DataProviderStatus>('/system/data-provider')).data,
};

export default {
  market: marketApi,
  options: optionsApi,
  indicators: indicatorsApi,
  journal: journalApi,
  risk: riskApi,
  ai: aiApi,
  scanner: scannerApi,
  alerts: alertsApi,
  strategies: strategiesApi,
  decisionSignals: decisionSignalsApi,
  agentAnalysis: agentAnalysisApi,
  system: systemApi,
};
