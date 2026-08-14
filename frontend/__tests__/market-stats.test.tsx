import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithClient } from './helpers/test-utils';
import { MarketStats } from '@/components/dashboard/market-stats';

jest.mock('@/lib/api', () => ({
  marketApi: {
    getStats: jest.fn(),
  },
}));

const getStats = require('@/lib/api').marketApi.getStats as jest.Mock;

afterEach(() => {
  jest.clearAllMocks();
});

describe('MarketStats tile', () => {
  it('renders loading skeleton initially', async () => {
    let resolve: (v: unknown) => void = () => {};
    getStats.mockReturnValue(
      new Promise((res) => {
        resolve = res;
      })
    );
    renderWithClient(<MarketStats />);
    // While pending, no "Retry" / values should be shown.
    expect(screen.queryByText('Retry')).not.toBeInTheDocument();
  });

  it('renders live market stats', async () => {
    getStats.mockResolvedValue({
      data: {
        advances: 1247,
        declines: 892,
        unchanged: 60,
        india_vix: 14.56,
        india_vix_change_percent: -5.09,
        nifty_pcr: 0.87,
        source: 'live',
        timestamp: '2026-01-01T10:00:00Z',
        is_stale: false,
      },
    });
    renderWithClient(<MarketStats />);
    await waitFor(() => {
      expect(screen.getByText('Advances')).toBeInTheDocument();
      expect(screen.getByText('1,247')).toBeInTheDocument();
      expect(screen.getByText('892')).toBeInTheDocument();
      expect(screen.getByText('0.87')).toBeInTheDocument();
    });
    // Live data: no fallback banner.
    expect(screen.queryByText('Live data unavailable')).not.toBeInTheDocument();
  });

  it('renders fallback banner when source is unavailable', async () => {
    getStats.mockResolvedValue({
      data: {
        advances: null,
        declines: null,
        unchanged: null,
        india_vix: null,
        india_vix_change_percent: null,
        nifty_pcr: null,
        source: 'unavailable',
        timestamp: '2026-01-01T10:00:00Z',
        is_stale: false,
      },
    });
    renderWithClient(<MarketStats />);
    await waitFor(() => {
      expect(screen.getByText('Live data unavailable')).toBeInTheDocument();
      // N/A shown for null values, never fabricated zeros.
      expect(screen.getAllByText('N/A').length).toBeGreaterThan(0);
    });
  });

  it('renders error state with retry button on failure', async () => {
    getStats.mockResolvedValue({
      data: null,
      error: 'NSE market data is temporarily unavailable',
    });
    renderWithClient(<MarketStats />);
    await waitFor(() => {
      expect(screen.getByText('Market stats unavailable')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });

  it('re-fetches when Retry is clicked', async () => {
    getStats.mockResolvedValueOnce({ data: null, error: 'down' });
    getStats.mockResolvedValueOnce({
      data: {
        advances: 10,
        declines: 5,
        unchanged: 1,
        india_vix: 14,
        india_vix_change_percent: 0,
        nifty_pcr: 1,
        source: 'live',
        timestamp: '2026-01-01T10:00:00Z',
        is_stale: false,
      },
    });
    renderWithClient(<MarketStats />);
    const retry = await screen.findByText('Retry');
    await userEvent.click(retry);
    await waitFor(() => {
      expect(screen.getByText('10')).toBeInTheDocument();
    });
  });
});
