import { render, screen, waitFor } from '@testing-library/react';
import ScannerPage from '@/app/(dashboard)/scanner/page';

jest.mock('@/lib/api', () => ({
  scannerApi: {
    getScanResults: jest.fn(),
  },
}));

const getScanResults = require('@/lib/api').scannerApi
  .getScanResults as jest.Mock;

afterEach(() => {
  jest.clearAllMocks();
});

const liveRow = {
  id: 'RELIANCE_volume_spike_0',
  symbol: 'RELIANCE',
  name: 'Reliance Industries',
  scan_type: 'volume_spike',
  direction: 'bullish',
  confidence: 82.5,
  price: 1316.0,
  change_percent: 1.42,
  volume_ratio: 2.1,
  details: { atr: 12.34 },
  timestamp: '2026-01-01T10:00:00Z',
  source: 'yfinance',
  status: 'live',
};

// Regression: the backend serializes NaN closes as JSON null (halted
// sessions / bad provider rows). The page must render N/A instead of
// crashing on null.toFixed().
const nullPriceRow = {
  ...liveRow,
  id: 'PREMIERENE_volume_spike_1',
  symbol: 'PREMIERENE',
  name: 'Premier Energies Ltd',
  price: null,
  change_percent: null,
  details: { atr: 28.54, change_percent: null },
};

describe('ScannerPage', () => {
  it('renders scan results with prices', async () => {
    getScanResults.mockResolvedValue({ data: [liveRow] });
    render(<ScannerPage />);
    await waitFor(() => {
      expect(screen.getByText('RELIANCE')).toBeInTheDocument();
    });
    expect(screen.getByText('₹1,316.00')).toBeInTheDocument();
    expect(screen.getByText('+1.42%')).toBeInTheDocument();
  });

  it('renders N/A for null price/change_percent without crashing', async () => {
    getScanResults.mockResolvedValue({ data: [nullPriceRow] });
    render(<ScannerPage />);
    await waitFor(() => {
      expect(screen.getByText('PREMIERENE')).toBeInTheDocument();
    });
    const naCells = screen.getAllByText('N/A');
    expect(naCells.length).toBeGreaterThanOrEqual(2);
  });

  it('renders mixed live and null-price rows together', async () => {
    getScanResults.mockResolvedValue({ data: [liveRow, nullPriceRow] });
    render(<ScannerPage />);
    await waitFor(() => {
      expect(screen.getByText('RELIANCE')).toBeInTheDocument();
      expect(screen.getByText('PREMIERENE')).toBeInTheDocument();
    });
  });

  it('renders error state with retry on failure', async () => {
    getScanResults.mockResolvedValue({
      data: null,
      error: 'connection refused',
    });
    render(<ScannerPage />);
    await waitFor(() => {
      expect(screen.getByText('connection refused')).toBeInTheDocument();
    });
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });
});
