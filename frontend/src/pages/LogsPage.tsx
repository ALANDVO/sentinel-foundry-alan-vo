import { useState, useEffect, useMemo } from 'react';
import { useLogs } from '../hooks';
import { RefreshCw, AlertCircle, CheckCircle, Clock, TrendingUp, ChevronDown, ChevronUp, X } from 'lucide-react';
import { RequestLog } from '../types';
import { formatRelativeTime, formatDuration, getStatusColor, cn } from '../utils/format';

const statusBadge = (s: number) => getStatusColor(s || 0);
const badgeClass = (c: string) => c === 'success' ? 'badge-success' : c === 'error' ? 'badge-error' : c === 'warning' ? 'badge-warning' : 'badge-neutral';

interface Filters {
  provider_id: string;
  session_id: string;
  status_code: number | undefined;
  error_only: boolean;
  hours: number;
}

function ExpandedLog({ log, onClose }: { log: RequestLog; onClose: () => void }) {
  return (
    <div className="border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4 space-y-4">
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>ID: <code className="font-mono">{log.id}</code></div>
        <div>Provider: {log.provider_name || '—'}</div>
        <div>Method: {log.method}</div>
        <div>Path: <code className="font-mono">{log.path}</code></div>
        <div>Status: {log.response_status || '—'}</div>
        <div>Latency: {formatDuration(log.latency_ms)}</div>
        <div>Session: {log.session_id || '—'}</div>
        <div>Time: {formatRelativeTime(log.created_at)}</div>
      </div>
      {log.error_message && (
        <div className="p-3 rounded bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <p className="text-sm font-medium text-red-800 dark:text-red-300">Error:</p>
          <pre className="text-xs text-red-700 dark:text-red-400 mt-1 whitespace-pre-wrap">{log.error_message}</pre>
        </div>
      )}
      {log.request_body && (
        <details className="group">
          <summary className="text-sm font-medium cursor-pointer flex items-center gap-2">
            <ChevronDown className="w-4 h-4 transition-transform group-open:rotate-180" />
            Request Body
          </summary>
          <pre className="mt-2 p-3 bg-slate-100 dark:bg-slate-900 rounded text-xs overflow-x-auto text-slate-900 dark:text-slate-100">{JSON.stringify(log.request_body, null, 2)}</pre>
        </details>
      )}
      {log.response_body && (
        <details className="group">
          <summary className="text-sm font-medium cursor-pointer flex items-center gap-2">
            <ChevronDown className="w-4 h-4 transition-transform group-open:rotate-180" />
            Response Body
          </summary>
          <pre className="mt-2 p-3 bg-slate-100 dark:bg-slate-900 rounded text-xs overflow-x-auto text-slate-900 dark:text-slate-100">{JSON.stringify(log.response_body, null, 2)}</pre>
        </details>
      )}
      <div className="flex justify-end">
        <button onClick={onClose} className="btn btn-ghost btn-sm gap-1"><X className="w-4 h-4" /> Close</button>
      </div>
    </div>
  );
}


export function LogsPage() {
  const { logs, stats, loading, fetchLogs, fetchStats } = useLogs();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<Filters>({ provider_id: '', session_id: '', status_code: undefined, error_only: false, hours: 24 });
  const [expanded, setExpanded] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => { fetchLogs({ ...filters, page, page_size: 50 }); fetchStats(24); }, [fetchLogs, fetchStats, filters, page]);

  const handleRefresh = () => { setRefreshing(true); fetchLogs({ ...filters, page, page_size: 50 }); fetchStats(24); setRefreshing(false); };
  const badge = (s: number) => badgeClass(statusBadge(s));
  const expandedLog = useMemo(() => logs.find(l => l.id === expanded), [logs, expanded]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div><h1 className="text-2xl font-bold">Request Logs</h1><p className="text-slate-600 dark:text-slate-400">Monitor and debug provider requests</p></div>
        <button onClick={handleRefresh} disabled={refreshing || loading} className="btn btn-secondary gap-2"><RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} /> Refresh</button>
      </div>

      <div className="card p-5">
        <h3 className="font-semibold mb-4">Filters</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <div><label className="label">Provider</label><select value={filters.provider_id} onChange={e => { setFilters(p => ({ ...p, provider_id: e.target.value })); setPage(1); }} className="input"><option value="">All</option>{logs.map(l => l.provider_id && l.provider_name && <option key={l.provider_id} value={l.provider_id}>{l.provider_name}</option>)}</select></div>
          <div><label className="label">Session ID</label><input value={filters.session_id} onChange={e => { setFilters(p => ({ ...p, session_id: e.target.value })); setPage(1); }} className="input" placeholder="Filter by session..."/></div>
          <div><label className="label">Status</label><input type="number" value={filters.status_code} onChange={e => { const v = e.target.value; setFilters(p => ({ ...p, status_code: v ? parseInt(v) : undefined })); setPage(1); }} className="input" placeholder="200, 500..."/></div>
          <div><label className="label">Range</label><select value={filters.hours} onChange={e => { setFilters(p => ({ ...p, hours: parseInt(e.target.value) })); setPage(1); }} className="input"><option value={1}>1h</option><option value={6}>6h</option><option value={24}>24h</option><option value={168}>7d</option></select></div>
          <div className="flex items-end"><label className="flex items-center gap-2 cursor-pointer w-full"><input type="checkbox" checked={filters.error_only} onChange={e => setFilters(p => ({ ...p, error_only: e.target.checked }))} className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"/>Errors only</label></div>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="card p-5"><div className="flex justify-between"><div><p className="text-sm text-slate-500 dark:text-slate-400">Total</p><p className="text-3xl font-bold">{stats.total_requests}</p></div><TrendingUp className="w-6 h-6 text-blue-500"/></div></div>
          <div className="card p-5"><div className="flex justify-between"><div><p className="text-sm text-slate-500 dark:text-slate-400">Success</p><p className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">{stats.successful_requests}</p></div><CheckCircle className="w-6 h-6 text-emerald-600"/></div></div>
          <div className="card p-5"><div className="flex justify-between"><div><p className="text-sm text-slate-500 dark:text-slate-400">Failed</p><p className="text-3xl font-bold text-red-600 dark:text-red-400">{stats.failed_requests}</p></div><AlertCircle className="w-6 h-6 text-red-600"/></div></div>
          <div className="card p-5"><div className="flex justify-between"><div><p className="text-sm text-slate-500 dark:text-slate-400">Avg Latency</p><p className="text-3xl font-bold">{formatDuration(stats.avg_latency_ms)}</p></div><Clock className="w-6 h-6 text-slate-600"/></div></div>
        </div>
      )}

      <div className="card">
        <div className="overflow-x-auto"><table><thead><tr><th>Time</th><th>Provider</th><th>Method</th><th>Path</th><th>Status</th><th>Latency</th><th>Session</th><th className="w-12"></th></tr></thead><tbody>
          {loading && !logs.length ? <tr><td colSpan={8} className="py-12 text-center"><div className="flex flex-col items-center gap-3"><div className="spinner"/><p className="text-slate-500 dark:text-slate-400">Loading...</p></div></td></tr> : !logs.length ? <tr><td colSpan={8} className="py-12 text-center"><div className="empty-state"><Clock className="w-12 h-12"/><h3>No requests</h3><p>Requests appear here</p></div></td></tr> : logs.map(l => (
            <tr key={l.id} className={expanded === l.id ? 'bg-slate-50 dark:bg-slate-800/50' : ''}>
              <td className="text-sm text-slate-500 dark:text-slate-400 font-mono whitespace-nowrap">{formatRelativeTime(l.created_at)}</td>
              <td>{l.provider_name ? <span className="font-medium">{l.provider_name}</span> : <span className="text-slate-500 dark:text-slate-400">—</span>}</td>
              <td className="font-mono text-sm">{l.method}</td>
              <td className="font-mono text-sm truncate max-w-xs">{l.path}</td>
              <td><span className={cn('badge', badge(l.response_status || 0))}>{l.response_status || '—'}</span></td>
              <td className="font-mono text-sm">{formatDuration(l.latency_ms)}</td>
              <td className="font-mono text-xs text-slate-500 dark:text-slate-400 truncate max-w-xs">{l.session_id ? l.session_id.slice(0, 8) + '...' : '—'}</td>
              <td><button onClick={() => setExpanded(expanded === l.id ? null : l.id)} className="btn btn-ghost p-1.5" aria-label={expanded === l.id ? 'Collapse' : 'Expand'}>{expanded === l.id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}</button></td>
            </tr>
          ))}
        </tbody></table></div>
        {expandedLog && <ExpandedLog log={expandedLog} onClose={() => setExpanded(null)} />}
        {(stats && 'total_pages' in stats && typeof stats.total_pages === 'number' && stats.total_pages > 1) && (
          <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-700 flex justify-between">
            <p className="text-sm text-slate-600 dark:text-slate-400">Page {(stats as any).page} of {(stats as any).total_pages} ({(stats as any).total} total)</p>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1 || loading} className="btn btn-secondary btn-sm">Prev</button>
              <button onClick={() => setPage(p => Math.min((stats as any).total_pages, p + 1))} disabled={page === (stats as any).total_pages || loading} className="btn btn-secondary btn-sm">Next</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}