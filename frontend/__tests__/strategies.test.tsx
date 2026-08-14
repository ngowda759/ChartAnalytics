import { screen, waitFor } from '@testing-library/react';
import { renderWithClient } from './helpers/test-utils';

jest.mock('@/lib/api', () => ({
  strategiesApi: {
    getStrategies: jest.fn(),
  },
}));

const getStrategies = require('@/lib/api').strategiesApi
  .getStrategies as jest.Mock;

afterEach(() => {
  jest.clearAllMocks();
});

// The Strategies page is a client component with heavy useQuery usage; test the
// data contract that matters most: no fabricated metrics and a loading state.
describe('Strategies page', () => {
  it('renders real strategies with N/A metrics (backend has no metrics)', async () => {
    getStrategies.mockResolvedValue({
      data: [
        {
          id: 's1',
          name: 'EMA Cross',
          type: 'EMA_CROSSOVER',
          description: 'desc',
          is_active: true,
        },
      ],
    });
    const mod = await import('@/app/(dashboard)/strategies/page');
    renderWithClient(<mod.default />);
    await waitFor(() => {
      expect(screen.getByText('EMA Cross')).toBeInTheDocument();
      // Win Rate metric is N/A (not fabricated) since backend has no metrics.
      expect(screen.getAllByText('N/A').length).toBeGreaterThan(0);
    });
  });

  it('renders empty state when there are no strategies', async () => {
    getStrategies.mockResolvedValue({ data: [] });
    const mod = await import('@/app/(dashboard)/strategies/page');
    renderWithClient(<mod.default />);
    await waitFor(() => {
      expect(
        screen.getByText('No strategies yet. Create one to get started.')
      ).toBeInTheDocument();
    });
  });

  it('renders error state on failure', async () => {
    getStrategies.mockResolvedValue({ data: null, error: 'unauthorized' });
    const mod = await import('@/app/(dashboard)/strategies/page');
    renderWithClient(<mod.default />);
    await waitFor(() => {
      expect(
        screen.getByText(/Unable to load strategies/)
      ).toBeInTheDocument();
    });
  });
});
