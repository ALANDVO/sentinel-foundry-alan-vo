import { createContext, useContext, useState, ReactNode, useCallback } from 'react';
import { api } from '../api/client';
import type { Provider, ProviderCreate, ProviderUpdate, ProviderTestResponse } from '../types';
import toast from 'react-hot-toast';

interface ProviderContextType {
  providers: Provider[];
  loading: boolean;
  error: string | null;
  pagination: { page: number; page_size: number; total: number; total_pages: number } | null;
  fetchProviders: (page?: number, page_size?: number) => Promise<void>;
  createProvider: (data: ProviderCreate) => Promise<Provider | null>;
  updateProvider: (id: string, data: ProviderUpdate) => Promise<Provider | null>;
  deleteProvider: (id: string) => Promise<boolean>;
  testProvider: (id: string) => Promise<ProviderTestResponse | null>;
  refreshHealth: (id: string) => Promise<void>;
}

const ProviderContext = createContext<ProviderContextType | null>(null);

export function ProviderStore({ children }: { children: ReactNode }) {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState<{ page: number; page_size: number; total: number; total_pages: number } | null>(null);

  const fetchProviders = useCallback(async (page = 1, page_size = 20) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listProviders({ page, page_size });
      setProviders(response.items);
      setPagination({
        page: response.page,
        page_size: response.page_size,
        total: response.total,
        total_pages: response.total_pages,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch providers';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  const createProvider = useCallback(async (data: ProviderCreate) => {
    try {
      const provider = await api.createProvider(data);
      setProviders(prev => [provider, ...prev]);
      toast.success('Provider created');
      return provider;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create provider';
      toast.error(message);
      return null;
    }
  }, []);

  const updateProvider = useCallback(async (id: string, data: ProviderUpdate) => {
    try {
      const provider = await api.updateProvider(id, data);
      setProviders(prev => prev.map(p => p.id === id ? provider : p));
      toast.success('Provider updated');
      return provider;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update provider';
      toast.error(message);
      return null;
    }
  }, []);

  const deleteProvider = useCallback(async (id: string) => {
    try {
      await api.deleteProvider(id);
      setProviders(prev => prev.filter(p => p.id !== id));
      toast.success('Provider deleted');
      return true;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to delete provider';
      toast.error(message);
      return false;
    }
  }, []);

  const testProvider = useCallback(async (id: string) => {
    try {
      const result = await api.testProvider(id);
      toast.success(result.success ? 'Provider test passed' : `Provider test failed: ${result.error}`);
      return result;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to test provider';
      toast.error(message);
      return null;
    }
  }, []);

  const refreshHealth = useCallback(async (id: string) => {
    try {
      const health = await api.getProviderHealth(id);
      setProviders(prev => prev.map(p => p.id === id ? { ...p, health } : p));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to refresh health';
      toast.error(message);
    }
  }, []);

  return (
    <ProviderContext.Provider value={{
      providers,
      loading,
      error,
      pagination,
      fetchProviders,
      createProvider,
      updateProvider,
      deleteProvider,
      testProvider,
      refreshHealth,
    }}>
      {children}
    </ProviderContext.Provider>
  );
}

export function useProviders() {
  const context = useContext(ProviderContext);
  if (!context) {
    throw new Error('useProviders must be used within a ProviderStore');
  }
  return context;
}