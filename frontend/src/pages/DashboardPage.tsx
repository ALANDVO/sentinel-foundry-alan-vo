import { useEffect } from 'react';
import { useAuth } from '../hooks';
import { useProviders } from '../hooks';
import { Server, CheckCircle, AlertCircle, Activity, Clock, TrendingUp } from 'lucide-react';
import { formatRelativeTime, formatDuration, cn } from '../utils/format';

export function DashboardPage() {
  const { user } = useAuth();
  const { providers, loading, fetchProviders, refreshHealth } = useProviders();

  useEffect(() => {
    fetchProviders();
    const interval = setInterval(() => {
      providers.forEach(p => refreshHealth(p.id));
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchProviders, providers, refreshHealth]);

  const healthyCount = providers.filter(p => p.health?.healthy).length;
  const totalCount = providers.length;
  const circuitOpenCount = providers.filter(p => p.health?.circuit_open).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Dashboard</h1>
          <p className="text-slate-600 dark:text-slate-400 mt-1">
            Overview of provider health and system status
          </p>
        </div>
        <div className="flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-1">
            <Activity className="w-4 h-4" />
            Live
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Total Providers</p>
              <p className="text-3xl font-bold text-slate-900 dark:text-white">{totalCount}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
              <Server className="w-6 h-6 text-blue-700 dark:text-blue-300" />
            </div>
          </div>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Healthy</p>
              <p className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">{healthyCount}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
              <CheckCircle className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
            </div>
          </div>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Circuit Open</p>
              <p className="text-3xl font-bold text-amber-600 dark:text-amber-400">{circuitOpenCount}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-amber-600 dark:text-amber-400" />
            </div>
          </div>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Unhealthy</p>
              <p className="text-3xl font-bold text-red-600 dark:text-red-400">{totalCount - healthyCount}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="p-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Providers</h2>
        </div>
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Provider</th>
                <th>Type</th>
                <th>Model</th>
                <th>Status</th>
                <th>Latency</th>
                <th>Circuit</th>
                <th>Last Check</th>
                <th className="w-24"></th>
              </tr>
            </thead>
            <tbody>
              {loading && providers.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <div className="spinner" />
                      <p className="text-slate-500 dark:text-slate-400">Loading providers...</p>
                    </div>
                  </td>
                </tr>
              ) : providers.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center">
                    <div className="empty-state">
                      <Server className="w-12 h-12" />
                      <h3>No providers configured</h3>
                      <p>Add your first provider to get started</p>
                    </div>
                  </td>
                </tr>
              ) : (
                providers.map((provider) => (
                  <tr key={provider.id}>
                    <td>
                      <div>
                        <p className="font-medium text-slate-900 dark:text-white">{provider.name}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400 truncate max-w-xs">
                          {provider.base_url}
                        </p>
                      </div>
                    </td>
                    <td>
                      <span className="badge badge-neutral">{provider.type}</span>
                    </td>
                    <td className="font-mono text-sm text-slate-600 dark:text-slate-400">
                      {provider.model || '—'}
                    </td>
                    <td>
                      {provider.health ? (
                        <span className={cn(
                          'badge',
                          provider.health.healthy ? 'badge-success' : 'badge-error'
                        )}>
                          {provider.health.healthy ? 'Healthy' : 'Unhealthy'}
                        </span>
                      ) : (
                        <span className="badge badge-neutral">Unknown</span>
                      )}
                    </td>
                    <td className="font-mono text-sm">
                      {provider.health?.latency_ms !== undefined
                        ? formatDuration(provider.health.latency_ms)
                        : '—'}
                    </td>
                    <td>
                      {provider.health?.circuit_open ? (
                        <span className="badge badge-warning">Open</span>
                      ) : (
                        <span className="badge badge-success">Closed</span>
                      )}
                    </td>
                    <td className="text-sm text-slate-500 dark:text-slate-400">
                      {provider.health ? formatRelativeTime(provider.health.checked_at) : 'Never'}
                    </td>
                    <td>
                      <button
                        onClick={() => refreshHealth(provider.id)}
                        disabled={loading}
                        className="btn btn-ghost btn-sm p-1.5"
                        aria-label={`Refresh health for ${provider.name}`}
                      >
                        <Activity className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <a href="/providers" className="btn btn-secondary w-full justify-start gap-3">
              <Server className="w-5 h-5" />
              Add Provider
            </a>
            <a href="/sessions" className="btn btn-secondary w-full justify-start gap-3">
              <Clock className="w-5 h-5" />
              View Sessions
            </a>
            <a href="/logs" className="btn btn-secondary w-full justify-start gap-3">
              <TrendingUp className="w-5 h-5" />
              View Logs
            </a>
          </div>
        </div>

        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">System Info</h3>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">Environment</dt>
              <dd className="font-mono text-slate-900 dark:text-white">Development</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">Version</dt>
              <dd className="font-mono text-slate-900 dark:text-white">1.0.0</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">User</dt>
              <dd className="font-mono text-slate-900 dark:text-white">{user?.preferred_username || user?.sub}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500 dark:text-slate-400">Roles</dt>
              <dd className="font-mono text-slate-900 dark:text-white">{user?.roles?.join(', ') || 'None'}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}