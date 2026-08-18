'use client';

import { useState, useEffect } from 'react';
import { systemApi, type DataProviderStatus } from '@/lib/api';

// NOTE: There is no backend admin API yet, so this panel intentionally does NOT
// fabricate user counts, API-call counters, log lines, or a user table. Every
// surface that lacks a real data source shows a truthful "not available" /
// "coming soon" placeholder. The one real signal we *do* have is the live
// market-data provider status (/system/data-provider), which is shown as-is.

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState('overview');
  const [provider, setProvider] = useState<DataProviderStatus | null>(null);
  const [providerLoading, setProviderLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      const p = await systemApi.dataProvider();
      if (active) setProvider(p ?? null);
      if (active) setProviderLoading(false);
    })();
    return () => { active = false; };
  }, []);

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'info': return 'bg-blue-100 text-blue-800';
      case 'warning': return 'bg-yellow-100 text-yellow-800';
      case 'error': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Admin Panel</h1>
        <p className="text-muted-foreground mt-1">
          System status & configuration. Admin management features (users,
          strategies, logs) are not backed by a data source yet.
        </p>
      </div>

      {/* Stats Grid — only the provider card shows real data */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-lg border p-6">
          <p className="text-sm text-muted-foreground">Market Provider</p>
          <p className="text-2xl font-bold capitalize">
            {providerLoading ? '…' : provider?.provider ?? 'N/A'}
          </p>
        </div>
        <div className="rounded-lg border p-6">
          <p className="text-sm text-muted-foreground">Active Strategies</p>
          <p className="text-2xl font-bold text-muted-foreground">N/A</p>
          <p className="text-xs text-muted-foreground mt-1">No admin data source</p>
        </div>
        <div className="rounded-lg border p-6">
          <p className="text-sm text-muted-foreground">Active Alerts</p>
          <p className="text-2xl font-bold text-muted-foreground">N/A</p>
          <p className="text-xs text-muted-foreground mt-1">No admin data source</p>
        </div>
        <div className="rounded-lg border p-6">
          <p className="text-sm text-muted-foreground">API Calls Today</p>
          <p className="text-2xl font-bold text-muted-foreground">N/A</p>
          <p className="text-xs text-muted-foreground mt-1">No admin data source</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b">
        <nav className="-mb-px flex space-x-8">
          {['overview', 'users', 'strategies', 'alerts', 'logs', 'settings'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-4 px-1 border-b-2 font-medium text-sm capitalize ${
                activeTab === tab
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="rounded-lg border">
        {activeTab === 'overview' && (
          <div className="p-6">
            <h2 className="text-xl font-semibold mb-4">System Overview</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="border rounded-lg p-4">
                <h3 className="font-medium mb-2">Market-Data Provider</h3>
                <span className={`px-2 py-1 text-xs rounded ${provider?.connected ? 'bg-green-100 text-green-800 dark:bg-green-500/10 dark:text-green-600' : 'bg-red-100 text-red-800 dark:bg-red-500/10 dark:text-red-600'}`}>
                  {providerLoading ? 'Checking…' : provider?.connected ? 'Connected' : 'Not connected'}
                </span>
                <p className="text-sm text-muted-foreground mt-2 capitalize">
                  Provider: {provider?.provider ?? '—'} · Options: {provider?.options ? 'available' : 'unavailable'}
                </p>
              </div>
              <div className="border rounded-lg p-4">
                <h3 className="font-medium mb-2">Environment</h3>
                <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800 dark:bg-blue-500/10 dark:text-blue-600">
                  {process.env.NODE_ENV === 'production' ? 'Production' : 'Development'}
                </span>
              </div>
              <div className="border rounded-lg p-4">
                <h3 className="font-medium mb-2">Database Backend</h3>
                <span className="px-2 py-1 text-xs rounded bg-yellow-100 text-yellow-800 dark:bg-yellow-500/10 dark:text-yellow-600">
                  Local JSON (Fallback)
                </span>
                <p className="text-sm text-muted-foreground mt-2">Firebase not configured</p>
              </div>
              <div className="border rounded-lg p-4">
                <h3 className="font-medium mb-2">User / Audit Data</h3>
                <p className="text-sm text-muted-foreground">No admin data source configured.</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'users' && (
          <div className="p-6 text-center text-muted-foreground">
            <p className="text-lg">User management not available</p>
            <p className="text-sm mt-2">
              No backend admin API is configured, so no user list is shown.
            </p>
          </div>
        )}

        {activeTab === 'logs' && (
          <div className="p-6 text-center text-muted-foreground">
            <p className="text-lg">System logs not available</p>
            <p className="text-sm mt-2">
              No log streaming source is configured.
            </p>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="p-6">
            <h2 className="text-xl font-semibold mb-4">System Settings</h2>
            <div className="space-y-6">
              <div>
                <h3 className="font-medium mb-2">Database Configuration</h3>
                <div className="bg-muted/40 p-4 rounded-lg">
                  <p className="text-sm text-muted-foreground mb-2"><strong>Backend:</strong> Local JSON (Fallback)</p>
                  <p className="text-xs text-muted-foreground">Configure Firebase credentials in .env to use Firestore</p>
                </div>
              </div>
              <div>
                <h3 className="font-medium mb-2">Market-Data Provider</h3>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-3 bg-muted/40 rounded">
                    <span className="text-sm capitalize">{provider?.provider ?? '—'}</span>
                    <span className={`text-xs ${provider?.connected ? 'text-green-600' : 'text-red-600'}`}>
                      {provider?.connected ? 'Connected' : 'Not connected'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-muted/40 rounded">
                    <span className="text-sm">Options / OI feed</span>
                    <span className={`text-xs ${provider?.options ? 'text-green-600' : 'text-yellow-600'}`}>
                      {provider?.options ? 'Available' : 'Not configured'}
                    </span>
                  </div>
                </div>
              </div>
              <div>
                <h3 className="font-medium mb-2">Danger Zone</h3>
                <div className="space-y-2">
                  <button className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 dark:hover:bg-red-500/10">
                    Clear All Data
                  </button>
                  <button className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 dark:hover:bg-red-500/10">
                    Reset to Defaults
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {(activeTab === 'strategies' || activeTab === 'alerts') && (
          <div className="p-6 text-center text-muted-foreground">
            <p className="text-lg">{activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} management coming soon</p>
            <p className="text-sm mt-2">This feature is under development</p>
          </div>
        )}
      </div>
    </div>
  );
}
