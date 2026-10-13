import { useAuth } from '../hooks';
import { User, Shield, Server, Database, Globe, Bell, Key, Moon, Sun } from 'lucide-react';
import { useState } from 'react';

export function SettingsPage() {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<'account' | 'security' | 'appearance' | 'system'>('account');
  const [darkMode, setDarkMode] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  const tabs = [
    { id: 'account', label: 'Account', icon: User },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'appearance', label: 'Appearance', icon: Moon },
    { id: 'system', label: 'System', icon: Server },
  ];

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await logout();
    } finally {
      setLoggingOut(false);
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Settings</h1>
        <p className="text-slate-600 dark:text-slate-400 mt-1">
          Manage your account and preferences
        </p>
      </div>

      <div className="card">
        <div className="border-b border-slate-200 dark:border-slate-700">
          <nav className="flex gap-1 p-1" aria-label="Settings tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
                aria-current={activeTab === tab.id ? 'page' : undefined}
              >
                <tab.icon size={16} />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'account' && (
            <div className="space-y-6">
              <div className="flex items-center gap-4 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
                <div className="w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                  <User className="w-8 h-8 text-blue-700 dark:text-blue-300" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                    {user?.preferred_username || user?.email || user?.sub}
                  </h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{user?.email || 'No email'}</p>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {user?.roles?.map(role => (
                      <span key={role} className="badge badge-neutral text-xs">{role}</span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="label">User ID</label>
                  <input type="text" value={user?.sub || ''} readOnly className="input bg-slate-50 dark:bg-slate-800" />
                </div>
                <div>
                  <label className="label">Email</label>
                  <input type="email" value={user?.email || ''} readOnly className="input bg-slate-50 dark:bg-slate-800" />
                </div>
                <div>
                  <label className="label">Username</label>
                  <input type="text" value={user?.preferred_username || ''} readOnly className="input bg-slate-50 dark:bg-slate-800" />
                </div>
                <div>
                  <label className="label">Authentication</label>
                  <input type="text" value="Keycloak OIDC" readOnly className="input bg-slate-50 dark:bg-slate-800" />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Session Management</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
                    <div>
                      <p className="font-medium text-slate-900 dark:text-white">Active Sessions</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">Manage your active login sessions</p>
                    </div>
                    <button className="btn btn-secondary btn-sm" disabled>View Sessions</button>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
                    <div>
                      <p className="font-medium text-slate-900 dark:text-white">Revoke All Sessions</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">Sign out of all devices except current</p>
                    </div>
                    <button className="btn btn-secondary btn-sm" disabled>Revoke</button>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white mb-4">API Access</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
                    <div>
                      <p className="font-medium text-slate-900 dark:text-white">API Keys</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">Manage API keys for programmatic access</p>
                    </div>
                    <button className="btn btn-secondary btn-sm" disabled>Manage Keys</button>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
                <button onClick={handleLogout} disabled={loggingOut} className="btn btn-danger gap-2 w-full sm:w-auto">
                  <Key className="w-4 h-4" />
                  {loggingOut ? 'Signing out...' : 'Sign Out Everywhere'}
                </button>
              </div>
            </div>
          )}

          {activeTab === 'appearance' && (
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Theme</h3>
                <div className="grid grid-cols-2 gap-4">
                  <button
                    onClick={() => setDarkMode(false)}
                    className={`p-4 rounded-lg border-2 transition-all ${
                      !darkMode
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                    }`}
                  >
                    <div className="flex items-center justify-center gap-3 mb-2">
                      <Sun className="w-6 h-6 text-amber-500" />
                      <span className="font-medium text-slate-900 dark:text-white">Light</span>
                    </div>
                    <p className="text-sm text-slate-500 dark:text-slate-400 text-center">
                      Clean and bright interface
                    </p>
                  </button>
                  <button
                    onClick={() => setDarkMode(true)}
                    className={`p-4 rounded-lg border-2 transition-all ${
                      darkMode
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                    }`}
                  >
                    <div className="flex items-center justify-center gap-3 mb-2">
                      <Moon className="w-6 h-6 text-indigo-500" />
                      <span className="font-medium text-slate-900 dark:text-white">Dark</span>
                    </div>
                    <p className="text-sm text-slate-500 dark:text-slate-400 text-center">
                      Easy on the eyes for late nights
                    </p>
                  </button>
                </div>
              </div>

              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Density</h3>
                <div className="grid grid-cols-3 gap-4">
                  {['Comfortable', 'Compact', 'Spacious'].map((density, i) => (
                    <button
                      key={density}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        i === 0
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                      }`}
                    >
                      <p className="font-medium text-slate-900 dark:text-white">{density}</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                        {i === 0 ? 'Default spacing' : i === 1 ? 'More content' : 'More breathing room'}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'system' && (
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white mb-4">System Information</h3>
                <dl className="space-y-3">
                  <div className="flex justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                    <dt className="text-slate-500 dark:text-slate-400">Version</dt>
                    <dd className="font-mono text-slate-900 dark:text-white">1.0.0</dd>
                  </div>
                  <div className="flex justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                    <dt className="text-slate-500 dark:text-slate-400">Environment</dt>
                    <dd className="font-mono text-slate-900 dark:text-white">Development</dd>
                  </div>
                  <div className="flex justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                    <dt className="text-slate-500 dark:text-slate-400">API Base URL</dt>
                    <dd className="font-mono text-slate-900 dark:text-white">http://localhost:8000</dd>
                  </div>
                  <div className="flex justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                    <dt className="text-slate-500 dark:text-slate-400">Keycloak URL</dt>
                    <dd className="font-mono text-slate-900 dark:text-white">http://localhost:8080</dd>
                  </div>
                  <div className="flex justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                    <dt className="text-slate-500 dark:text-slate-400">Database</dt>
                    <dd className="font-mono text-slate-900 dark:text-white">SQLite (local)</dd>
                  </div>
                </dl>
              </div>

              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Debug</h3>
                <div className="space-y-3">
                  <button className="btn btn-secondary w-full sm:w-auto justify-start gap-3" disabled>
                    <Database className="w-4 h-4" />
                    View Database Schema
                  </button>
                  <button className="btn btn-secondary w-full sm:w-auto justify-start gap-3" disabled>
                    <Globe className="w-4 h-4" />
                    Test Provider Connectivity
                  </button>
                  <button className="btn btn-secondary w-full sm:w-auto justify-start gap-3" disabled>
                    <Bell className="w-4 h-4" />
                    View Audit Logs
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}