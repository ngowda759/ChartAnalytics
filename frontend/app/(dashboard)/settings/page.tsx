'use client';

import { useState, useEffect } from 'react';
import { Save, CheckCircle, XCircle, Loader2 } from 'lucide-react';

// Types
interface APIKeys {
  angelOne: {
    enabled: boolean;
    apiKey: string;
    clientCode: string;
    password: string;
    totpSecret: string;
  };
  kiteConnect: {
    enabled: boolean;
    apiKey: string;
    accessToken: string;
  };
}

interface TradingMetrics {
  winRate: number;
  avgWin: number;
  avgLoss: number;
  maxDrawdown: number;
  sharpeRatio: number;
  profitFactor: number;
  totalTrades: number;
  profitableTrades: number;
  avgHoldingTime: string;
  bestTrade: number;
  worstTrade: number;
}

const defaultAPIKeys: APIKeys = {
  angelOne: {
    enabled: false,
    apiKey: '',
    clientCode: '',
    password: '',
    totpSecret: '',
  },
  kiteConnect: {
    enabled: false,
    apiKey: '',
    accessToken: '',
  },
};

const defaultMetrics: TradingMetrics = {
  winRate: 65,
  avgWin: 2500,
  avgLoss: -1200,
  maxDrawdown: -5000,
  sharpeRatio: 1.8,
  profitFactor: 2.1,
  totalTrades: 156,
  profitableTrades: 101,
  avgHoldingTime: '45 mins',
  bestTrade: 8500,
  worstTrade: -3200,
};

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile');
  const [apiKeys, setAPIKeys] = useState<APIKeys>(defaultAPIKeys);
  const [metrics, setMetrics] = useState<TradingMetrics>(defaultMetrics);
  const [testingConnection, setTestingConnection] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<{ [key: string]: 'success' | 'error' | null }>({});
  const [saved, setSaved] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    const savedKeys = localStorage.getItem('apiKeys');
    const savedMetrics = localStorage.getItem('tradingMetrics');
    if (savedKeys) setAPIKeys(JSON.parse(savedKeys));
    if (savedMetrics) setMetrics(JSON.parse(savedMetrics));
  }, []);

  const handleSave = () => {
    localStorage.setItem('apiKeys', JSON.stringify(apiKeys));
    localStorage.setItem('tradingMetrics', JSON.stringify(metrics));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const testConnection = async (provider: 'angelOne' | 'kiteConnect') => {
    setTestingConnection(provider);
    setConnectionStatus({ ...connectionStatus, [provider]: null });
    
    // Simulate API test
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const isSuccess = provider === 'angelOne' 
      ? apiKeys.angelOne.apiKey.length > 5 
      : apiKeys.kiteConnect.apiKey.length > 5;
    
    setConnectionStatus({ ...connectionStatus, [provider]: isSuccess ? 'success' : 'error' });
    setTestingConnection(null);
  };

  const tabs = [
    { id: 'profile', label: 'Profile' },
    { id: 'trading', label: 'Trading' },
    { id: 'notifications', label: 'Notifications' },
    { id: 'display', label: 'Display' },
    { id: 'api', label: 'API Keys' },
    { id: 'metrics', label: 'Trading Metrics' },
    { id: 'data', label: 'Data & Backup' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-500 mt-1">Manage your account and preferences</p>
        </div>
        <button
          onClick={handleSave}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          {saved ? <CheckCircle className="h-4 w-4" /> : <Save className="h-4 w-4" />}
          {saved ? 'Saved!' : 'Save Changes'}
        </button>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-64 flex-shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-50 text-blue-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 bg-white rounded-lg shadow p-6">
          {activeTab === 'api' && (
            <div className="space-y-8">
              <h2 className="text-xl font-semibold">API Keys Configuration</h2>
              <p className="text-gray-500 text-sm">
                Configure your data provider API keys for real-time market data. Keys are stored locally in your browser.
              </p>

              {/* Angel One Section */}
              <div className="border rounded-lg p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <span className="text-blue-700 font-bold text-lg">A</span>
                    </div>
                    <div>
                      <h3 className="font-medium">Angel One SmartAPI</h3>
                      <p className="text-xs text-gray-500">Free WebSocket streaming, TOTP 2FA</p>
                    </div>
                  </div>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={apiKeys.angelOne.enabled}
                      onChange={(e) => setAPIKeys({
                        ...apiKeys,
                        angelOne: { ...apiKeys.angelOne, enabled: e.target.checked }
                      })}
                      className="rounded text-blue-600"
                    />
                    <span className="text-sm">Enable</span>
                  </label>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                    <input
                      type="password"
                      value={apiKeys.angelOne.apiKey}
                      onChange={(e) => setAPIKeys({
                        ...apiKeys,
                        angelOne: { ...apiKeys.angelOne, apiKey: e.target.value }
                      })}
                      placeholder="Enter Angel One API key"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Client Code</label>
                    <input
                      type="text"
                      value={apiKeys.angelOne.clientCode}
                      onChange={(e) => setAPIKeys({
                        ...apiKeys,
                        angelOne: { ...apiKeys.angelOne, clientCode: e.target.value }
                      })}
                      placeholder="Your Angel One client ID"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                    <input
                      type="password"
                      value={apiKeys.angelOne.password}
                      onChange={(e) => setAPIKeys({
                        ...apiKeys,
                        angelOne: { ...apiKeys.angelOne, password: e.target.value }
                      })}
                      placeholder="Your Angel One password"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">TOTP Secret</label>
                    <input
                      type="password"
                      value={apiKeys.angelOne.totpSecret}
                      onChange={(e) => setAPIKeys({
                        ...apiKeys,
                        angelOne: { ...apiKeys.angelOne, totpSecret: e.target.value }
                      })}
                      placeholder="2FA secret from Angel One app"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
                
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => testConnection('angelOne')}
                    disabled={testingConnection === 'angelOne' || !apiKeys.angelOne.apiKey}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 flex items-center gap-2"
                  >
                    {testingConnection === 'angelOne' ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : connectionStatus.angelOne === 'success' ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : connectionStatus.angelOne === 'error' ? (
                      <XCircle className="h-4 w-4 text-red-600" />
                    ) : null}
                    Test Connection
                  </button>
                  {connectionStatus.angelOne === 'success' && (
                    <span className="text-sm text-green-600">Connected successfully!</span>
                  )}
                  {connectionStatus.angelOne === 'error' && (
                    <span className="text-sm text-red-600">Connection failed. Check your credentials.</span>
                  )}
                </div>
                
                <p className="text-xs text-gray-500">
                  Get your API key from: <a href="https://www.angelone.in/smart-api" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Angel One SmartAPI</a>
                </p>
              </div>

              {/* Kite Connect Section */}
              <div className="border rounded-lg p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                      <span className="text-green-700 font-bold text-lg">K</span>
                    </div>
                    <div>
                      <h3 className="font-medium">Zerodha Kite Connect</h3>
                      <p className="text-xs text-gray-500">Free for personal use, OAuth authentication</p>
                    </div>
                  </div>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={apiKeys.kiteConnect.enabled}
                      onChange={(e) => setAPIKeys({
                        ...apiKeys,
                        kiteConnect: { ...apiKeys.kiteConnect, enabled: e.target.checked }
                      })}
                      className="rounded text-blue-600"
                    />
                    <span className="text-sm">Enable</span>
                  </label>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                    <input
                      type="password"
                      value={apiKeys.kiteConnect.apiKey}
                      onChange={(e) => setAPIKeys({
                        ...apiKeys,
                        kiteConnect: { ...apiKeys.kiteConnect, apiKey: e.target.value }
                      })}
                      placeholder="Enter Kite Connect API key"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Access Token</label>
                    <input
                      type="password"
                      value={apiKeys.kiteConnect.accessToken}
                      onChange={(e) => setAPIKeys({
                        ...apiKeys,
                        kiteConnect: { ...apiKeys.kiteConnect, accessToken: e.target.value }
                      })}
                      placeholder="Generate via OAuth flow"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
                
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => testConnection('kiteConnect')}
                    disabled={testingConnection === 'kiteConnect' || !apiKeys.kiteConnect.apiKey}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 flex items-center gap-2"
                  >
                    {testingConnection === 'kiteConnect' ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : connectionStatus.kiteConnect === 'success' ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : connectionStatus.kiteConnect === 'error' ? (
                      <XCircle className="h-4 w-4 text-red-600" />
                    ) : null}
                    Test Connection
                  </button>
                  {connectionStatus.kiteConnect === 'success' && (
                    <span className="text-sm text-green-600">Connected successfully!</span>
                  )}
                  {connectionStatus.kiteConnect === 'error' && (
                    <span className="text-sm text-red-600">Connection failed. Check your credentials.</span>
                  )}
                </div>
                
                <p className="text-xs text-gray-500">
                  Get your API key from: <a href="https://developers.kite.trade" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Kite Connect Developers</a>
                </p>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-sm text-yellow-800">
                  <strong>Note:</strong> API keys are stored locally in your browser. They are not sent to any external server.
                  For production use, configure these keys in your backend environment variables.
                </p>
              </div>
            </div>
          )}

          {activeTab === 'metrics' && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold">Trading Metrics Configuration</h2>
              <p className="text-gray-500 text-sm">
                Configure your trading performance metrics. These values are used for risk calculations and performance tracking.
              </p>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Win Rate (%)</label>
                  <input
                    type="number"
                    value={metrics.winRate}
                    onChange={(e) => setMetrics({ ...metrics, winRate: Number(e.target.value) })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    min="0"
                    max="100"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Avg Win (₹)</label>
                  <input
                    type="number"
                    value={metrics.avgWin}
                    onChange={(e) => setMetrics({ ...metrics, avgWin: Number(e.target.value) })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Avg Loss (₹)</label>
                  <input
                    type="number"
                    value={metrics.avgLoss}
                    onChange={(e) => setMetrics({ ...metrics, avgLoss: Number(e.target.value) })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Max Drawdown (₹)</label>
                  <input
                    type="number"
                    value={metrics.maxDrawdown}
                    onChange={(e) => setMetrics({ ...metrics, maxDrawdown: Number(e.target.value) })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Sharpe Ratio</label>
                  <input
                    type="number"
                    value={metrics.sharpeRatio}
                    onChange={(e) => setMetrics({ ...metrics, sharpeRatio: Number(e.target.value) })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    step="0.1"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Profit Factor</label>
                  <input
                    type="number"
                    value={metrics.profitFactor}
                    onChange={(e) => setMetrics({ ...metrics, profitFactor: Number(e.target.value) })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    step="0.1"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Total Trades</label>
                  <input
                    type="number"
                    value={metrics.totalTrades}
                    onChange={(e) => setMetrics({ ...metrics, totalTrades: Number(e.target.value) })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Profitable Trades</label>
                  <input
                    type="number"
                    value={metrics.profitableTrades}
                    onChange={(e) => setMetrics({ ...metrics, profitableTrades: Number(e.target.value) })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Avg Holding Time</label>
                  <input
                    type="text"
                    value={metrics.avgHoldingTime}
                    onChange={(e) => setMetrics({ ...metrics, avgHoldingTime: e.target.value })}
                    placeholder="e.g., 45 mins"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Best Trade (₹)</label>
                  <input
                    type="number"
                    value={metrics.bestTrade}
                    onChange={(e) => setMetrics({ ...metrics, bestTrade: Number(e.target.value) })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Worst Trade (₹)</label>
                  <input
                    type="number"
                    value={metrics.worstTrade}
                    onChange={(e) => setMetrics({ ...metrics, worstTrade: Number(e.target.value) })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Calculated Metrics */}
              <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                <h3 className="font-medium text-sm">Calculated Metrics</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">Expectancy</p>
                    <p className="font-medium">₹{((metrics.avgWin * metrics.winRate / 100) + (metrics.avgLoss * (100 - metrics.winRate) / 100)).toFixed(0)}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Risk/Reward</p>
                    <p className="font-medium">{metrics.avgLoss !== 0 ? (Math.abs(metrics.avgWin / metrics.avgLoss)).toFixed(2) : 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Loss Rate</p>
                    <p className="font-medium">{(100 - metrics.winRate).toFixed(1)}%</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Avg Risk/Trade</p>
                    <p className="font-medium">₹{Math.abs(metrics.avgLoss).toFixed(0)}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'profile' && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold">Profile Settings</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                  <input
                    type="text"
                    defaultValue="Trader"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input
                    type="email"
                    defaultValue="trader@example.com"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                  <input
                    type="tel"
                    defaultValue="+91 98765 43210"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'trading' && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold">Trading Settings</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Default Risk Per Trade (%)</label>
                  <input
                    type="number"
                    defaultValue={2}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    min="0.5"
                    max="10"
                    step="0.5"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Max Daily Loss (%)</label>
                  <input
                    type="number"
                    defaultValue={5}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    min="1"
                    max="20"
                    step="0.5"
                  />
                </div>
                <div className="space-y-2">
                  <label className="flex items-center gap-2">
                    <input type="checkbox" defaultChecked className="rounded text-blue-600" />
                    <span className="text-sm text-gray-700">Auto-save trades to journal</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="checkbox" defaultChecked className="rounded text-blue-600" />
                    <span className="text-sm text-gray-700">Confirm before executing trades</span>
                  </label>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold">Notification Preferences</h2>
              <div className="space-y-3">
                {['Email Alerts', 'Push Notifications', 'Trade Alerts', 'Strategy Alerts'].map((item) => (
                  <label key={item} className="flex items-center justify-between">
                    <span className="text-sm text-gray-700">{item}</span>
                    <input type="checkbox" defaultChecked className="rounded text-blue-600" />
                  </label>
                ))}
                <label className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">Market Alerts</span>
                  <input type="checkbox" className="rounded text-blue-600" />
                </label>
              </div>
            </div>
          )}

          {activeTab === 'display' && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold">Display Settings</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Theme</label>
                  <select className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                    <option value="light">Light</option>
                    <option value="dark">Dark</option>
                    <option value="system">System</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Default Chart Type</label>
                  <select className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                    <option value="candlestick">Candlestick</option>
                    <option value="line">Line</option>
                    <option value="area">Area</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="flex items-center gap-2">
                    <input type="checkbox" defaultChecked className="rounded text-blue-600" />
                    <span className="text-sm text-gray-700">Show volume on charts</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="checkbox" defaultChecked className="rounded text-blue-600" />
                    <span className="text-sm text-gray-700">Show grid lines</span>
                  </label>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'data' && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold">Data & Backup</h2>
              <div className="space-y-4">
                <button className="w-full px-3 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 text-left">
                  <span className="font-medium">Export Data</span>
                  <p className="text-sm text-gray-500">Download all your trading data as CSV</p>
                </button>
                <button className="w-full px-3 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 text-left">
                  <span className="font-medium">Import Data</span>
                  <p className="text-sm text-gray-500">Import trades from a CSV file</p>
                </button>
                <button className="w-full px-3 py-3 border border-red-300 rounded-lg hover:bg-red-50 text-left">
                  <span className="font-medium text-red-600">Clear All Data</span>
                  <p className="text-sm text-gray-500">Permanently delete all local data</p>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
