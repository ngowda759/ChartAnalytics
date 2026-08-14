import { screen, waitFor } from '@testing-library/react';
import { renderWithClient } from './helpers/test-utils';
import { RecentAlerts } from '@/components/dashboard/recent-alerts';

jest.mock('@/lib/api', () => ({
  alertsApi: {
    getNotifications: jest.fn(),
  },
}));

const getNotifications = require('@/lib/api').alertsApi
  .getNotifications as jest.Mock;

afterEach(() => {
  jest.clearAllMocks();
});

const sample = [
  {
    id: '1',
    type: 'ema_cross',
    symbol: 'NIFTY',
    message: 'NIFTY crossed above 20 EMA',
    timestamp: '2026-01-01T09:55:00Z',
    is_read: false,
  },
  {
    id: '2',
    type: 'breakout',
    symbol: 'BANKNIFTY',
    message: 'Resistance breakout',
    timestamp: '2026-01-01T09:45:00Z',
    is_read: true,
  },
];

describe('RecentAlerts tile', () => {
  it('renders live alert notifications', async () => {
    getNotifications.mockResolvedValue({ data: sample });
    renderWithClient(<RecentAlerts />);
    await waitFor(() => {
      expect(screen.getByText('NIFTY')).toBeInTheDocument();
      expect(screen.getByText('NIFTY crossed above 20 EMA')).toBeInTheDocument();
      expect(screen.getByText('BANKNIFTY')).toBeInTheDocument();
    });
  });

  it('renders empty state when there are no alerts', async () => {
    getNotifications.mockResolvedValue({ data: [] });
    renderWithClient(<RecentAlerts />);
    await waitFor(() => {
      expect(screen.getByText('No recent alerts')).toBeInTheDocument();
    });
  });

  it('renders error state with retry on failure', async () => {
    getNotifications.mockResolvedValue({
      data: null,
      error: 'connection refused',
    });
    renderWithClient(<RecentAlerts />);
    await waitFor(() => {
      expect(screen.getByText('Unable to load alerts')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });
});
