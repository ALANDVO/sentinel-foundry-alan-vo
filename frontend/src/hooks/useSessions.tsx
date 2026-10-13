import { createContext, useContext, useState, ReactNode, useCallback } from 'react';
import { api } from '../api/client';
import type { Session, SessionCreate, SessionUpdate, Message, MessageCreate } from '../types';
import toast from 'react-hot-toast';

interface SessionContextType {
  sessions: Session[];
  currentSession: Session | null;
  loading: boolean;
  error: string | null;
  pagination: { page: number; page_size: number; total: number; total_pages: number } | null;
  fetchSessions: (page?: number, page_size?: number) => Promise<void>;
  getSession: (id: string) => Promise<Session | null>;
  createSession: (data: SessionCreate) => Promise<Session | null>;
  updateSession: (id: string, data: SessionUpdate) => Promise<Session | null>;
  deleteSession: (id: string) => Promise<boolean>;
  addMessage: (sessionId: string, message: MessageCreate) => Promise<Message | null>;
  exportSession: (id: string) => Promise<void>;
  setCurrentSession: (session: Session | null) => void;
}

const SessionContext = createContext<SessionContextType | null>(null);

export function SessionStore({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState<{ page: number; page_size: number; total: number; total_pages: number } | null>(null);

  const fetchSessions = useCallback(async (page = 1, page_size = 20) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listSessions({ page, page_size });
      setSessions(response.items);
      setPagination({
        page: response.page,
        page_size: response.page_size,
        total: response.total,
        total_pages: response.total_pages,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch sessions';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  const getSession = useCallback(async (id: string) => {
    try {
      const session = await api.getSession(id);
      return session;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch session';
      toast.error(message);
      return null;
    }
  }, []);

  const createSession = useCallback(async (data: SessionCreate) => {
    try {
      const session = await api.createSession(data);
      setSessions(prev => [session, ...prev]);
      toast.success('Session created');
      return session;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create session';
      toast.error(message);
      return null;
    }
  }, []);

  const updateSession = useCallback(async (id: string, data: SessionUpdate) => {
    try {
      const session = await api.updateSession(id, data);
      setSessions(prev => prev.map(s => s.id === id ? session : s));
      if (currentSession?.id === id) {
        setCurrentSession(session);
      }
      toast.success('Session updated');
      return session;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update session';
      toast.error(message);
      return null;
    }
  }, [currentSession]);

  const deleteSession = useCallback(async (id: string) => {
    try {
      await api.deleteSession(id);
      setSessions(prev => prev.filter(s => s.id !== id));
      if (currentSession?.id === id) {
        setCurrentSession(null);
      }
      toast.success('Session deleted');
      return true;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to delete session';
      toast.error(message);
      return false;
    }
  }, [currentSession]);

  const addMessage = useCallback(async (sessionId: string, message: MessageCreate) => {
    try {
      const msg = await api.addMessage(sessionId, message);
      if (currentSession?.id === sessionId) {
        setCurrentSession(prev => prev ? {
          ...prev,
          messages: [...(prev.messages || []), msg],
          message_count: prev.message_count + 1,
        } : null);
      }
      return msg;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to add message';
      toast.error(message);
      return null;
    }
  }, [currentSession]);

  const exportSession = useCallback(async (id: string) => {
    try {
      const blob = await api.exportSession(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `session-${id}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Session exported');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to export session';
      toast.error(message);
    }
  }, []);

  return (
    <SessionContext.Provider value={{
      sessions,
      currentSession,
      loading,
      error,
      pagination,
      fetchSessions,
      getSession,
      createSession,
      updateSession,
      deleteSession,
      addMessage,
      exportSession,
      setCurrentSession,
    }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSessions() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSessions must be used within a SessionStore');
  }
  return context;
}