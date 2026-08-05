'use client';

import { useState } from 'react';

interface SystemStats {
  totalUsers: number;
  activeStrategies: number;
  activeAlerts: number;
  apiCallsToday: number;
}

interface LogEntry {
  id: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
  source: string;
}

const mockStats: SystemStats = {
  totalUsers: 156,
  activeStrategies: 42,
  activeAlerts: 89,
  apiCallsToday: 12453,
};

const mockLogs: LogEntry[] = [
  { id: '1', level: 'info', message: 'Market data updated successfully', timestamp: '2024-01-15 09:30:00', source: 'scheduler' },
  { id: '2', level: 'warning', message: 'High API latency detected: 250ms', timestamp: '2024-01-15 09:28:00', source: 'api' },
  { id: '3', level: 'error', message: 'Failed to fetch NIFTY data', timestamp: '2024-01-15 09:25:00', source: 'market_data' },
  { id: '4', level: 'info', message: 'User created new strategy', timestamp: '2024-01-15 09:20:00', source: 'user' },
  { id: '5', level: 'info', message: 'Alert triggered: EMA Cross', timestamp: '2024-01-15 09:15:00', source: 'alerts' },
];

const mockUsers = [
  { id: '1', name: 'John Doe', email: 'john@example.com', plan: 'Pro', status: 'active', joinedAt: '2024-01-01' },
  { id: '2', name: 'Jane Smith', email: 'jane@example.com', plan: 'Free', status: 'active', joinedAt: '2024-01-05' },
  { id: '3', name: 'Bob Wilson', email: 'bob@example.com', plan: 'Pro', status: 'inactive', joinedAt: '2023-12-15' },
];

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats] = useState<SystemStats>(mockStats);
  const [logs] = useState<LogEntry[]>(mockLogs);

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
        <h1 className="text-3xl font-bold text-gray-900">Admin Panel</h1>
        <p className="text-gray-500 mt-1">Manage users, strategies, and system settings</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Total Users</p>
          <p className="text-3xl font-bold text-gray-900">{stats.totalUsers}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Active Strategies</p>
          <p className="text-3xl font-bold text-green-600">{stats.activeStrategies}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Active Alerts</p>
          <p className="text-3xl font-bold text-blue-600">{stats.activeAlerts}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">API Calls Today</p>
          <p className="text-3xl font-bold text-purple-600">{stats.apiCallsToday.toLocaleString()}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {['overview', 'users', 'strategies', 'alerts', 'logs', 'settings'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-4 px-1 border-b-2 font-medium text-sm capitalize ${
                activeTab === tab
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-lg shadow">
        {activeTab === 'overview' && (
          <div className="p-6">
            <h2 className="text-xl font-semibold mb-4">System Overview</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="border rounded-lg p-4">
                <h3 className="font-medium mb-2">Database Backend</h3>
                <span className="px-2 py-1 text-xs rounded bg-yellow-100 text-yellow-800">Local JSON (Fallback)</span>
                <p className="text-sm text-gray-500 mt-2">Firebase not configured</p>
              </div>
              <div className="border rounded-lg p-4">
                <h3 className="font-medium mb-2">API Status</h3>
                <span className="px-2 py-1 text-xs rounded bg-green-100 text-green-800">Operational</span>
                <p className="text-sm text-gray-500 mt-2">All systems normal</p>
              </div>
              <div className="border rounded-lg p-4">
                <h3 className="font-medium mb-2">Environment</h3>
                <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">Development</span>
              </div>
              <div className="border rounded-lg p-4">
                <h3 className="font-medium mb-2">Last Market Update</h3>
                <p className="text-sm text-gray-900">2024-01-15 09:30:00</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'users' && (
          <div className="p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">User Management</h2>
              <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                Export Users
              </button>
            </div>
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Plan</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {mockUsers.map((user) => (
                  <tr key={user.id}>
                    <td className="px-6 py-4 whitespace-nowrap">{user.name}</td>
                    <td className="px-6 py-4 whitespace-nowrap">{user.email}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs rounded ${user.plan === 'Pro' ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'}`}>
                        {user.plan}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs rounded ${user.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {user.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button className="text-blue-600 hover:text-blue-800 mr-3">Edit</button>
                      <button className="text-red-600 hover:text-red-800">Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'logs' && (
          <div className="p-6">
            <h2 className="text-xl font-semibold mb-4">System Logs</h2>
            <div className="space-y-2">
              {logs.map((log) => (
                <div key={log.id} className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                  <span className={`px-2 py-1 text-xs rounded uppercase font-medium ${getLevelColor(log.level)}`}>
                    {log.level}
                  </span>
                  <span className="text-sm text-gray-500 w-32">{log.timestamp}</span>
                  <span className="text-xs text-gray-400 w-24">[{log.source}]</span>
                  <span className="flex-1 text-sm">{log.message}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="p-6">
            <h2 className="text-xl font-semibold mb-4">System Settings</h2>
            <div className="space-y-6">
              <div>
                <h3 className="font-medium mb-2">Database Configuration</h3>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-2"><strong>Backend:</strong> Local JSON (Fallback)</p>
                  <p className="text-xs text-gray-500">Configure Firebase credentials in .env to use Firestore</p>
                </div>
              </div>
              <div>
                <h3 className="font-medium mb-2">API Keys</h3>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="text-sm">OpenAI API</span>
                    <span className="text-xs text-gray-500">Configured</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="text-sm">Telegram Bot</span>
                    <span className="text-xs text-yellow-500">Not configured</span>
                  </div>
                </div>
              </div>
              <div>
                <h3 className="font-medium mb-2">Danger Zone</h3>
                <div className="space-y-2">
                  <button className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50">
                    Clear All Data
                  </button>
                  <button className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50">
                    Reset to Defaults
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {(activeTab === 'strategies' || activeTab === 'alerts') && (
          <div className="p-6 text-center text-gray-500">
            <p className="text-lg">{activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} management coming soon</p>
            <p className="text-sm mt-2">This feature is under development</p>
          </div>
        )}
      </div>
    </div>
  );
}
