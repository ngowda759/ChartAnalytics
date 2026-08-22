import { render, screen, waitFor } from '@testing-library/react';
import JournalPage from '@/app/(dashboard)/journal/page';

jest.mock('@/lib/api', () => ({
  __esModule: true,
  default: {
    journal: {
      getTrades: jest.fn(),
      getPerformance: jest.fn(),
      createTrade: jest.fn(),
      updateTrade: jest.fn(),
    },
  },
}));

const journalApi = require('@/lib/api').default.journal;

afterEach(() => {
  jest.clearAllMocks();
});

// Real backend shape: snake_case, with sharpe/drawdown/avg_rr truthfully
// null (not derivable from a flat trade list).
const backendMetrics = {
  total_trades: 45,
  winning_trades: 28,
  losing_trades: 17,
  win_rate: 62.2,
  average_win: 1200,
  average_loss: 600,
  profit_factor: 1.72,
  sharpe_ratio: null,
  max_drawdown: null,
  max_drawdown_percent: null,
  total_pnl: 24500,
  expectancy: 544,
  avg_rr: null,
  monthly_returns: [],
  source: 'journal',
};

const backendTrades = [
  {
    id: 't1',
    user_id: 'user_1',
    symbol: 'RELIANCE',
    instrument: 'equity',
    type: 'long',
    entry: { price: 1300, quantity: 10, timestamp: '2026-01-01T09:30:00' },
    exit: { price: 1360, quantity: 10, timestamp: '2026-01-02T15:00:00' },
    status: 'closed',
    strategy: 'breakout',
    tags: [],
    notes: null,
    screenshots: [],
    pnl: 600,
    fees: null,
    created_at: '2026-01-01T09:30:00',
    updated_at: '2026-01-02T15:00:00',
  },
];

describe('JournalPage', () => {
  it('renders metrics from the snake_case backend response without crashing', async () => {
    journalApi.getTrades.mockResolvedValue({ data: [] });
    journalApi.getPerformance.mockResolvedValue({ data: backendMetrics });
    render(<JournalPage />);
    await waitFor(() => {
      expect(screen.getByText('62.2%')).toBeInTheDocument(); // Win Rate
    });
    expect(screen.getByText('₹24,500')).toBeInTheDocument(); // Total P&L
    expect(screen.getByText('1.72')).toBeInTheDocument(); // Profit Factor
    expect(screen.getByText('45')).toBeInTheDocument(); // Total Trades
  });

  it('shows N/A for null sharpe/drawdown/avg_rr instead of crashing', async () => {
    journalApi.getTrades.mockResolvedValue({ data: [] });
    journalApi.getPerformance.mockResolvedValue({ data: backendMetrics });
    render(<JournalPage />);
    await waitFor(() => {
      expect(screen.getByText('Sharpe Ratio')).toBeInTheDocument();
    });
    // sharpe_ratio, max_drawdown_percent and avg_rr are null -> N/A x3
    const naCells = screen.getAllByText('N/A');
    expect(naCells.length).toBeGreaterThanOrEqual(3);
  });

  it('renders trades from the snake_case backend shape', async () => {
    journalApi.getTrades.mockResolvedValue({ data: backendTrades });
    journalApi.getPerformance.mockResolvedValue({ data: backendMetrics });
    render(<JournalPage />);
    await waitFor(() => {
      expect(screen.getByText('RELIANCE')).toBeInTheDocument();
    });
    expect(screen.getByText('LONG')).toBeInTheDocument();
    expect(screen.getByText('closed')).toBeInTheDocument();
  });

  it('renders empty state when there are no trades', async () => {
    journalApi.getTrades.mockResolvedValue({ data: [] });
    journalApi.getPerformance.mockResolvedValue({ data: backendMetrics });
    render(<JournalPage />);
    await waitFor(() => {
      expect(screen.getByText('No trades found')).toBeInTheDocument();
    });
  });
});
