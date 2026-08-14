// API Client for ChartAnalytics Backend

const getApiBaseUrl = () => {
  // Use environment variable if set, otherwise use relative URL for proxy
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  // Fallback to relative URL (works with Next.js API proxy)
  if (typeof window !== 'undefined') {
    return '/api/v1';
  }
  // Server-side fallback for SSR
  return 'http://localhost:8000/api/v1';
};

const API_BASE_URL = getApiBaseUrl();

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
  extra?: Record<string, number> | null;
}

export interface ScreenerWidget {
  id: string;
  title: string;
  description?: string | null;
  timeframe: string;
  columns: string[];
  rows: ScreenerRow[];
  last_updated: string;
}

export interface ScreenerDashboard {
  id: string;
  name: string;
  author: string;
  description?: string | null;
  widgets: ScreenerWidget[];
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
export const marketApi = {
  getQuotes: () => fetchApi<any[]>('/market/quotes'),
  getIndices: () => fetchApi<any[]>('/market/indices'),
  getOHLC: (symbol: string, timeframe: string) =>
    fetchApi<any[]>(`/market/ohlc/${symbol}?timeframe=${timeframe}`),
};

// Option Chain API
export const optionsApi = {
  getChain: (symbol: string) => fetchApi<any>(`/options/chain/${symbol}`),
  getPCR: (symbol: string) => fetchApi<any>(`/options/pcr/${symbol}`),
  getMaxPain: (symbol: string) => fetchApi<any>(`/options/max-pain/${symbol}`),
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
  getScanResults: () => fetchApi<any[]>('/scanner/'),
  getBreakouts: () => fetchApi<any[]>('/scanner/breakouts'),
  getOIBuildups: () => fetchApi<any[]>('/scanner/oi-buildup'),
  getDashboard: (dashboardId: string) =>
    fetchApi<ScreenerDashboard>(`/scanner/dashboard/${dashboardId}`),
  getNseDashboard: () => fetchApi<ScreenerDashboard>('/scanner/nse-dashboard'),
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
}

export const decisionSignalsApi = {
  listSignals: (params?: {
    action?: DecisionAction;
    strategy?: string;
    min_score?: number;
    limit?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.action) qs.set('action', params.action);
    if (params?.strategy) qs.set('strategy', params.strategy);
    if (params?.min_score !== undefined)
      qs.set('min_score', String(params.min_score));
    if (params?.limit) qs.set('limit', String(params.limit));
    const query = qs.toString();
    return fetchApi<DecisionSignalListResponse>(
      `/decision-signals/signals${query ? `?${query}` : ''}`
    );
  },
  getStrategies: () => fetchApi<string[]>('/decision-signals/strategies'),
  getSignal: (signalId: string) =>
    fetchApi<DecisionSignal>(`/decision-signals/signals/${encodeURIComponent(signalId)}`),
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
};
