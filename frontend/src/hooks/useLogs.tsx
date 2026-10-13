import { createContext, useContext, useState, ReactNode, useCallback } from 'react';
import { api } from '../api/client';
import type { RequestLog, LogStats } from '../types';
import toast from 'react-hot-toast';

interface LogsContextType {
  logs: RequestLog[];
  stats: LogStats | null;
  loading: boolean;
  error: string | null;
  pagination: { page: number; page_size: number; total: number; total_pages: number } | null;
  fetchLogs: (params?: { page?: number; page_size?: number; provider_id?: string; session_id?: string; status_code?: number; error_only?: boolean; hours?: number }) => Promise<void>;
  fetchStats: (hours?: number) => Promise<void>;
}

const LogsContext = createContext<LogsContextType | null>(null);

export function LogsStore({ children }: { children: ReactNode }) {
  const [logs, setLogs] = useState<RequestLog[]>([]);
  const [stats, setStats] = useState<LogStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState<{ page: number; page_size: number; total: number; total_pages: number } | null>(null);

  const fetchLogs = useCallback(async (params?: { page?: number; page_size?: number; provider_id?: string; session_id?: string; status_code?: number; error_only?: boolean; hours?: number }) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listLogs(params);
      setLogs(response.items);
      setPagination({
        page: response.page,
        page_size: response.page_size,
        total: response.total,
        total_pages: response.total_pages,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch logs';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchStats = useCallback(async (hours = 24) => {
    try {
      const statsData = await api.getLogStats(hours);
      setStats(statsData);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch stats';
      toast.error(message);
    }
  }, []);

  return (
    <LogsContext.Provider value={{
      logs,
      stats,
      loading,
      error,
      pagination,
      fetchLogs,
      fetchStats,
    }}>
      {children}
    </LogsContext.Provider>
  );
}

export function useLogs() {
  const context = useContext(LogsContext);
  if (!context) {
    throw new Error('useLogs must be used within a LogsStore');
  }
  return context;
}