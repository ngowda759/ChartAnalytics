// User types
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'user' | 'admin';
  subscription: Subscription;
  preferences: UserPreferences;
  riskProfile: RiskProfile;
  createdAt: Date;
  updatedAt: Date;
}

export interface Subscription {
  tier: 'free' | 'pro' | 'enterprise';
  expiresAt: Date;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  defaultIndex: string;
  notifications: NotificationPreferences;
}

export interface NotificationPreferences {
  email: boolean;
  telegram: boolean;
  browser: boolean;
  alerts: AlertPreferences;
}

export interface AlertPreferences {
  emaCross: boolean;
  vwapCross: boolean;
  breakout: boolean;
  oiSpike: boolean;
  pcrShift: boolean;
  volumeSpike: boolean;
}

export interface RiskProfile {
  maxRiskPerTrade: number;
  maxDailyLoss: number;
  maxWeeklyLoss: number;
  maxPositionSize: number;
}

// Market data types
export interface MarketQuote {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  open: number;
  high: number;
  low: number;
  previousClose: number;
  volume: number;
  timestamp: Date;
}

export interface OHLC {
  timestamp: Date;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndexQuote extends MarketQuote {
  isIndex: true;
}

// Option chain types
export interface OptionChain {
  symbol: string;
  expiry: string;
  underlying: string;
  spotPrice: number;
  timestamp: Date;
  strikes: OptionStrike[];
  pcr: number;
  maxPain: number;
  totalCallOI: number;
  totalPutOI: number;
}

export interface OptionStrike {
  strike: number;
  call: OptionData;
  put: OptionData;
}

export interface OptionData {
  oi: number;
  change: number;
  volume: number;
  iv: number;
  ltp: number;
  bid: number;
  ask: number;
}

export interface OIAnalysis {
  type: 'buildup' | 'unwinding' | 'short_covering' | 'long_unwinding';
  callOI: number;
  putOI: number;
  change: number;
  interpretation: string;
}

export interface PCRAnalysis {
  value: number;
  interpretation: 'bullish' | 'bearish' | 'neutral';
  trend: 'rising' | 'falling' | 'stable';
}

// Technical indicators
export interface TechnicalIndicators {
  ema: EMAResult;
  rsi: number;
  macd: MACDResult;
  vwap: number;
  supertrend: SupertrendResult;
  bollingerBands: BollingerBandsResult;
  atr: number;
  adx: number;
}

export interface EMAResult {
  ema20: number;
  ema50: number;
  ema200: number;
  trend: 'bullish' | 'bearish' | 'neutral';
}

export interface MACDResult {
  macd: number;
  signal: number;
  histogram: number;
  crossover: 'bullish' | 'bearish' | 'none';
}

export interface SupertrendResult {
  value: number;
  direction: 'up' | 'down';
  isBreakout: boolean;
}

export interface BollingerBandsResult {
  upper: number;
  middle: number;
  lower: number;
  bandwidth: number;
  position: number;
}

// Scanner types
export interface ScanResult {
  id: string;
  symbol: string;
  type: ScanType;
  signal: 'bullish' | 'bearish' | 'neutral';
  confidence: number;
  price: number;
  change: number;
  details: Record<string, unknown>;
  timestamp: Date;
}

export type ScanType = 
  | 'breakout'
  | 'ema_cross'
  | 'volume_spike'
  | 'oi_buildup'
  | 'gapper';

export interface BreakoutSignal {
  symbol: string;
  type: 'resistance' | 'support';
  breakoutPrice: number;
  currentPrice: number;
  volumeRatio: number;
  confidence: number;
}

// Trade types
export interface Trade {
  id: string;
  userId: string;
  symbol: string;
  instrument: 'futures' | 'options' | 'equity';
  type: 'long' | 'short';
  entry: TradeEntry;
  exit?: TradeExit;
  status: 'open' | 'closed' | 'cancelled';
  strategy: string;
  tags: string[];
  notes?: string;
  screenshots?: string[];
  pnl?: number;
  fees?: number;
  createdAt: Date;
  updatedAt: Date;
}

export interface TradeEntry {
  price: number;
  quantity: number;
  timestamp: Date;
}

export interface TradeExit {
  price: number;
  quantity: number;
  timestamp: Date;
}

export interface PerformanceMetrics {
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  winRate: number;
  averageWin: number;
  averageLoss: number;
  profitFactor: number;
  sharpeRatio: number;
  maxDrawdown: number;
  maxDrawdownPercent: number;
  totalPnl: number;
  expectancy: number;
  avgRr: number;
  monthlyReturns: MonthlyReturn[];
}

export interface MonthlyReturn {
  month: string;
  return: number;
  trades: number;
}

// Strategy types
export interface Strategy {
  id: string;
  userId: string;
  name: string;
  type: StrategyType;
  description?: string;
  rules: StrategyRule[];
  parameters: Record<string, unknown>;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export type StrategyType =
  | 'ORB'
  | 'VWAP'
  | 'EMA_CROSSOVER'
  | 'MOMENTUM'
  | 'SCALPING'
  | 'OPTION_BUYING'
  | 'OPTION_SELLING'
  | 'CUSTOM';

export interface StrategyRule {
  id: string;
  type: 'indicator' | 'price' | 'volume' | 'time' | 'custom';
  indicator?: string;
  condition: '>' | '<' | '==' | '>=' | '<=' | 'crosses_above' | 'crosses_below';
  value: number | string;
  operator?: 'AND' | 'OR';
}

export interface BacktestResult {
  strategy: Strategy;
  period: BacktestPeriod;
  metrics: BacktestMetrics;
  trades: BacktestTrade[];
  equityCurve: EquityPoint[];
}

export interface BacktestPeriod {
  startDate: Date;
  endDate: Date;
}

export interface BacktestMetrics {
  totalReturn: number;
  annualizedReturn: number;
  winRate: number;
  profitFactor: number;
  sharpeRatio: number;
  sortinoRatio: number;
  maxDrawdown: number;
  maxDrawdownDuration: number;
  totalTrades: number;
  avgTradeDuration: number;
  recoveryFactor: number;
}

export interface BacktestTrade {
  entryDate: Date;
  exitDate: Date;
  symbol: string;
  type: 'long' | 'short';
  entryPrice: number;
  exitPrice: number;
  quantity: number;
  pnl: number;
  pnlPercent: number;
}

export interface EquityPoint {
  date: Date;
  equity: number;
  drawdown: number;
}

// AI types
export interface AIInsight {
  id: string;
  symbol: string;
  type: 'trend' | 'momentum' | 'support_resistance' | 'breakout' | 'general';
  title: string;
  description: string;
  confidence: number;
  bias: 'bullish' | 'bearish' | 'neutral';
  reasoning: string;
  indicators: string[];
  timestamp: Date;
}

export interface ChartAnalysis {
  id: string;
  symbol: string;
  patterns: ChartPattern[];
  levels: TradingLevels;
  bias: 'bullish' | 'bearish' | 'neutral';
  confidence: number;
  reasoning: string;
  timestamp: Date;
}

export interface ChartPattern {
  type: string;
  confidence: number;
  description: string;
}

export interface TradingLevels {
  entry: number;
  stopLoss: number;
  target1: number;
  target2: number;
  target3: number;
  riskReward: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export interface ChatResponse {
  message: ChatMessage;
  sources?: string[];
}

// Risk management types
export interface PositionSize {
  quantity: number;
  riskAmount: number;
  capitalRequired: number;
  riskPercent: number;
}

export interface RiskCalculation {
  positionSize: PositionSize;
  maxLoss: number;
  maxProfit: number;
  breakeven: number;
}

export interface DailyLimit {
  date: Date;
  maxLoss: number;
  currentLoss: number;
  remainingLoss: number;
  isLimitHit: boolean;
}

// Alert types
export interface Alert {
  id: string;
  userId: string;
  type: AlertType;
  symbol: string;
  condition: string;
  value: number;
  isActive: boolean;
  lastTriggered?: Date;
  createdAt: Date;
}

export type AlertType =
  | 'ema_cross'
  | 'vwap_cross'
  | 'breakout'
  | 'oi_spike'
  | 'pcr_shift'
  | 'volume_spike'
  | 'price_alert';

export interface AlertNotification {
  id: string;
  type: AlertType;
  symbol: string;
  message: string;
  timestamp: Date;
  isRead: boolean;
}
