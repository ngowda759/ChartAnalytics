'use client';

import { useState } from 'react';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile');
  const [settings, setSettings] = useState({
    profile: {
      name: 'Trader',
      email: 'trader@example.com',
      phone: '+91 98765 43210',
    },
    trading: {
      defaultRiskPercent: 2,
      defaultStopLoss: 2,
      maxDailyLoss: 5,
      autoSaveTrades: true,
      confirmTrades: true,
    },
    notifications: {
      emailAlerts: true,
      pushNotifications: true,
      tradeAlerts: true,
      marketAlerts: false,
      strategyAlerts: true,
    },
    display: {
      theme: 'light',
      chartType: 'candlestick',
      defaultTimeframe: '1D',
      showVolume: true,
      showGrid: true,
    },
  });

  const tabs = [
    { id: 'profile', label: 'Profile' },
    { id: 'trading', label: 'Trading' },
    { id: 'notifications', label: 'Notifications' },
    { id: 'display', label: 'Display' },
    { id: 'api', label: 'API Keys' },
    { id: 'data', label: 'Data & Backup' },
  ];

  const handleSave = () => {
    alert('Settings saved successfully!');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-500 mt-1">Manage your account and preferences</p>
        </div>
        <button
          onClick={handleSave}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Save Changes
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
          {activeTab === 'profile' && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold">Profile Settings</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                  <input
                    type="text"
                    value={settings.profile.name}
                    onChange={(e) => setSettings({
                      ...settings,
                      profile: { ...settings.profile, name: e.target.value }
                    })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input
                    type="email"
                    value={settings.profile.email}
                    onChange={(e) => setSettings({
                      ...settings,
                      profile: { ...settings.profile, email: e.target.value }
                    })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                  <input
                    type="tel"
                    value={settings.profile.phone}
                    onChange={(e) => setSettings({
                      ...settings,
                      profile: { ...settings.profile, phone: e.target.value }
                    })}
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Default Risk Per Trade (%)
                  </label>
                  <input
                    type="number"
                    value={settings.trading.defaultRiskPercent}
                    onChange={(e) => setSettings({
                      ...settings,
                      trading: { ...settings.trading, defaultRiskPercent: Number(e.target.value) }
                    })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    min="0.5"
                    max="10"
                    step="0.5"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max Daily Loss (%)
                  </label>
                  <input
                    type="number"
                    value={settings.trading.maxDailyLoss}
                    onChange={(e) => setSettings({
                      ...settings,
                      trading: { ...settings.trading, maxDailyLoss: Number(e.target.value) }
                    })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    min="1"
                    max="20"
                    step="0.5"
                  />
                </div>
                <div className="space-y-2">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={settings.trading.autoSaveTrades}
                      onChange={(e) => setSettings({
                        ...settings,
                        trading: { ...settings.trading, autoSaveTrades: e.target.checked }
                      })}
                      className="rounded text-blue-600"
                    />
                    <span className="text-sm text-gray-700">Auto-save trades to journal</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={settings.trading.confirmTrades}
                      onChange={(e) => setSettings({
                        ...settings,
                        trading: { ...settings.trading, confirmTrades: e.target.checked }
                      })}
                      className="rounded text-blue-600"
                    />
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
                <label className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">Email Alerts</span>
                  <input
                    type="checkbox"
                    checked={settings.notifications.emailAlerts}
                    onChange={(e) => setSettings({
                      ...settings,
                      notifications: { ...settings.notifications, emailAlerts: e.target.checked }
                    })}
                    className="rounded text-blue-600"
                  />
                </label>
                <label className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">Push Notifications</span>
                  <input
                    type="checkbox"
                    checked={settings.notifications.pushNotifications}
                    onChange={(e) => setSettings({
                      ...settings,
                      notifications: { ...settings.notifications, pushNotifications: e.target.checked }
                    })}
                    className="rounded text-blue-600"
                  />
                </label>
                <label className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">Trade Alerts</span>
                  <input
                    type="checkbox"
                    checked={settings.notifications.tradeAlerts}
                    onChange={(e) => setSettings({
                      ...settings,
                      notifications: { ...settings.notifications, tradeAlerts: e.target.checked }
                    })}
                    className="rounded text-blue-600"
                  />
                </label>
                <label className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">Market Alerts</span>
                  <input
                    type="checkbox"
                    checked={settings.notifications.marketAlerts}
                    onChange={(e) => setSettings({
                      ...settings,
                      notifications: { ...settings.notifications, marketAlerts: e.target.checked }
                    })}
                    className="rounded text-blue-600"
                  />
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
                  <select
                    value={settings.display.theme}
                    onChange={(e) => setSettings({
                      ...settings,
                      display: { ...settings.display, theme: e.target.value }
                    })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="light">Light</option>
                    <option value="dark">Dark</option>
                    <option value="system">System</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Default Chart Type</label>
                  <select
                    value={settings.display.chartType}
                    onChange={(e) => setSettings({
                      ...settings,
                      display: { ...settings.display, chartType: e.target.value }
                    })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="candlestick">Candlestick</option>
                    <option value="line">Line</option>
                    <option value="area">Area</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={settings.display.showVolume}
                      onChange={(e) => setSettings({
                        ...settings,
                        display: { ...settings.display, showVolume: e.target.checked }
                      })}
                      className="rounded text-blue-600"
                    />
                    <span className="text-sm text-gray-700">Show volume on charts</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={settings.display.showGrid}
                      onChange={(e) => setSettings({
                        ...settings,
                        display: { ...settings.display, showGrid: e.target.checked }
                      })}
                      className="rounded text-blue-600"
                    />
                    <span className="text-sm text-gray-700">Show grid lines</span>
                  </label>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'api' && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold">API Keys</h2>
              <p className="text-gray-500">Configure your data provider API keys for real-time market data.</p>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                  <input
                    type="password"
                    placeholder="Enter your API key"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                  Test Connection
                </button>
              </div>
            </div>
          )}

          {activeTab === 'data' && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold">Data & Backup</h2>
              <div className="space-y-4">
                <button className="w-full px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 text-left">
                  <span className="font-medium">Export Data</span>
                  <p className="text-sm text-gray-500">Download all your trading data as CSV</p>
                </button>
                <button className="w-full px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 text-left">
                  <span className="font-medium">Import Data</span>
                  <p className="text-sm text-gray-500">Import trades from a CSV file</p>
                </button>
                <button className="w-full px-4 py-3 border border-red-300 rounded-lg hover:bg-red-50 text-left">
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
