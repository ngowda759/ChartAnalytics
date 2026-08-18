import { screen, waitFor } from '@testing-library/react';
import { renderWithClient } from './helpers/test-utils';
import { PerformanceSummary } from '@/components/dashboard/performance-summary';

jest.mock('@/lib/api', () => ({
  journalApi: {
    getPerformance: jest.fn(),
  },
}));

const getPerformance = require('@/lib/api').journalApi
  .getPerformance as jest.Mock;

afterEach(() => {
  jest.clearAllMocks();
});

describe('PerformanceSummary tile', () => {
  it('renders real backend-derived metrics', async () => {
    getPerformance.mockResolvedValue({
      data: {
        total_trades: 45,
        winning_trades: 28,
        losing_trades: 17,
        win_rate: 62.2,
        average_win: 1200,
        average_loss: 600,
        profit_factor: 1.72,
        total_pnl: 24500,
        expectancy: 544,
        avg_rr: 1.85,
      },
    });
    renderWithClient(<PerformanceSummary />);
    await waitFor(() => {
      expect(screen.getByText('₹24,500')).toBeInTheDocument(); // Total P&L
      expect(screen.getByText('62.2%')).toBeInTheDocument(); // Win Rate
      expect(screen.getByText('1.85:1')).toBeInTheDocument(); // Avg R:R
      expect(screen.getByText('1.72')).toBeInTheDocument(); // Profit Factor
      expect(screen.getByText('45')).toBeInTheDocument(); // Total Trades
      expect(screen.getByText('28W / 17L')).toBeInTheDocument();
    });
  });

  it('shows N/A for non-derivable metrics instead of fabricating', async () => {
    // Non-zero trades so metrics render, but profit_factor / avg_rr are null
    // (non-derivable) -> must show N/A, never a fabricated value.
    getPerformance.mockResolvedValue({
      data: {
        total_trades: 5,
        winning_trades: 3,
        losing_trades: 2,
        win_rate: 60,
        average_win: 1000,
        average_loss: 500,
        profit_factor: null,
        total_pnl: 2000,
        expectancy: 300,
        avg_rr: null,
      },
    });
    renderWithClient(<PerformanceSummary />);
    await waitFor(() => {
      // avg_rr null -> N/A, never a fabricated ratio
      expect(screen.getAllByText('N/A').length).toBeGreaterThan(0);
      expect(screen.queryByText('1.85:1')).not.toBeInTheDocument();
    });
  });

  it('shows a truthful empty state when there are no trades', async () => {
    getPerformance.mockResolvedValue({
      data: {
        total_trades: 0,
        winning_trades: 0,
        losing_trades: 0,
        win_rate: 0,
        average_win: 0,
        average_loss: 0,
        profit_factor: 0,
        total_pnl: 0,
        expectancy: 0,
        avg_rr: 0,
      },
    });
    renderWithClient(<PerformanceSummary />);
    await waitFor(() => {
      expect(screen.getByText('No trading history available')).toBeInTheDocument();
    });
  });

  it('renders error state with retry on failure', async () => {
    getPerformance.mockResolvedValue({
      data: null,
      error: 'journal unavailable',
    });
    renderWithClient(<PerformanceSummary />);
    await waitFor(() => {
      expect(screen.getByText('Unable to load performance')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });
});
