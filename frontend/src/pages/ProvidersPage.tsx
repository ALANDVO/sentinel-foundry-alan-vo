import { useState, useEffect } from 'react';
import { useProviders } from '../hooks';
import { Plus, Edit, Trash2, Play, X, Loader2 } from 'lucide-react';
import { Provider, ProviderCreate } from '../types';

const PROVIDER_TYPES = [
  { value: 'openai-compatible', label: 'OpenAI Compatible (OpenRouter, LiteLLM, vLLM, etc.)' },
  { value: 'anthropic', label: 'Anthropic (Direct API)' },
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'ollama', label: 'Ollama (Local)' },
] as const;

export function ProvidersPage() {
  const { providers, loading, pagination, fetchProviders, createProvider, updateProvider, deleteProvider, testProvider } = useProviders();
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);
  const [formData, setFormData] = useState<ProviderCreate>({
    name: '',
    type: 'openai-compatible',
    base_url: '',
    api_key: '',
    model: '',
    enabled: true,
    priority: 0,
    timeout_seconds: 30,
    max_retries: 2,
  });
  const [submitting, setSubmitting] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);

  useEffect(() => {
    fetchProviders(page);
  }, [fetchProviders, page]);

  const handleOpenCreate = () => {
    setEditingProvider(null);
    setFormData({
      name: '',
      type: 'openai-compatible',
      base_url: '',
      api_key: '',
      model: '',
      enabled: true,
      priority: 0,
      timeout_seconds: 30,
      max_retries: 2,
    });
    setModalOpen(true);
  };

  const handleOpenEdit = (provider: Provider) => {
    setEditingProvider(provider);
    setFormData({
      name: provider.name,
      type: provider.type,
      base_url: provider.base_url,
      api_key: '',
      model: provider.model || '',
      enabled: provider.enabled,
      priority: provider.priority,
      timeout_seconds: provider.timeout_seconds,
      max_retries: provider.max_retries,
    });
    setModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (editingProvider) {
        await updateProvider(editingProvider.id, formData);
      } else {
        await createProvider(formData);
      }
      setModalOpen(false);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (provider: Provider) => {
    if (!confirm(`Delete provider "${provider.name}"? This cannot be undone.`)) return;
    await deleteProvider(provider.id);
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    try {
      await testProvider(id);
    } finally {
      setTesting(null);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    if (type === 'checkbox') {
      setFormData(prev => ({ ...prev, [name]: (e.target as HTMLInputElement).checked }));
    } else if (type === 'number') {
      setFormData(prev => ({ ...prev, [name]: parseInt(value, 10) || 0 }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Providers</h1>
          <p className="text-slate-600 dark:text-slate-400 mt-1">
            Configure and manage LLM providers
          </p>
        </div>
        <button onClick={handleOpenCreate} className="btn btn-primary gap-2">
          <Plus className="w-4 h-4" />
          Add Provider
        </button>
      </div>

      <div className="card">
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Base URL</th>
                <th>Model</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Enabled</th>
                <th className="w-48">Actions</th>
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
                      <Plus className="w-12 h-12" />
                      <h3>No providers configured</h3>
                      <p>Add your first provider to start routing requests</p>
                    </div>
                  </td>
                </tr>
              ) : (
                providers.map((provider) => (
                  <tr key={provider.id}>
                    <td className="font-medium text-slate-900 dark:text-white">{provider.name}</td>
                    <td><span className="badge badge-neutral">{provider.type}</span></td>
                    <td className="font-mono text-sm text-slate-600 dark:text-slate-400 truncate max-w-xs">{provider.base_url}</td>
                    <td className="font-mono text-sm text-slate-600 dark:text-slate-400">{provider.model || '—'}</td>
                    <td>
                      {provider.health ? (
                        <span className={provider.health.healthy ? 'badge badge-success' : 'badge badge-error'}>
                          {provider.health.healthy ? 'Healthy' : 'Unhealthy'}
                        </span>
                      ) : (
                        <span className="badge badge-neutral">Unknown</span>
                      )}
                    </td>
                    <td className="font-mono">{provider.priority}</td>
                    <td>
                      <span className={provider.enabled ? 'badge badge-success' : 'badge badge-neutral'}>
                        {provider.enabled ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleOpenEdit(provider)}
                          className="btn btn-ghost btn-sm p-1.5"
                          aria-label={`Edit ${provider.name}`}
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleTest(provider.id)}
                          disabled={testing === provider.id}
                          className="btn btn-ghost btn-sm p-1.5"
                          aria-label={`Test ${provider.name}`}
                        >
                          {testing === provider.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                        </button>
                        <button
                          onClick={() => handleDelete(provider)}
                          className="btn btn-ghost btn-sm p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                          aria-label={`Delete ${provider.name}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {pagination && pagination.total_pages > 1 && (
          <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Page {pagination.page} of {pagination.total_pages} ({pagination.total} total)
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={pagination.page === 1 || loading}
                className="btn btn-secondary btn-sm"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(p => Math.min(pagination.total_pages, p + 1))}
                disabled={pagination.page === pagination.total_pages || loading}
                className="btn btn-secondary btn-sm"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setModalOpen(false)}>
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="p-5 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                {editingProvider ? 'Edit Provider' : 'Add Provider'}
              </h2>
              <button onClick={() => setModalOpen(false)} className="btn btn-ghost p-1.5">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-5 space-y-4">
              <div>
                <label htmlFor="name" className="label">Name</label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  value={formData.name}
                  onChange={handleChange}
                  className="input"
                  required
                  placeholder="My OpenRouter"
                />
              </div>

              <div>
                <label htmlFor="type" className="label">Type</label>
                <select
                  id="type"
                  name="type"
                  value={formData.type}
                  onChange={handleChange}
                  className="input"
                  required
                >
                  {PROVIDER_TYPES.map(t => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="base_url" className="label">Base URL</label>
                <input
                  id="base_url"
                  name="base_url"
                  type="url"
                  value={formData.base_url}
                  onChange={handleChange}
                  className="input"
                  required
                  placeholder="https://api.openai.com/v1"
                />
              </div>

              <div>
                <label htmlFor="api_key" className="label">API Key (optional)</label>
                <input
                  id="api_key"
                  name="api_key"
                  type="password"
                  value={formData.api_key}
                  onChange={handleChange}
                  className="input"
                  placeholder={editingProvider ? 'Leave blank to keep current' : 'sk-...'}
                  autoComplete="new-password"
                />
              </div>

              <div>
                <label htmlFor="model" className="label">Model (optional)</label>
                <input
                  id="model"
                  name="model"
                  type="text"
                  value={formData.model}
                  onChange={handleChange}
                  className="input"
                  placeholder="gpt-4o-mini"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="priority" className="label">Priority</label>
                  <input
                    id="priority"
                    name="priority"
                    type="number"
                    value={formData.priority}
                    onChange={handleChange}
                    className="input"
                    min="-100"
                    max="100"
                  />
                </div>
                <div>
                  <label htmlFor="timeout_seconds" className="label">Timeout (seconds)</label>
                  <input
                    id="timeout_seconds"
                    name="timeout_seconds"
                    type="number"
                    value={formData.timeout_seconds}
                    onChange={handleChange}
                    className="input"
                    min="1"
                    max="300"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="max_retries" className="label">Max Retries</label>
                  <input
                    id="max_retries"
                    name="max_retries"
                    type="number"
                    value={formData.max_retries}
                    onChange={handleChange}
                    className="input"
                    min="0"
                    max="10"
                  />
                </div>
                <div className="flex items-end">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      name="enabled"
                      type="checkbox"
                      checked={formData.enabled}
                      onChange={handleChange}
                      className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-slate-700 dark:text-slate-300">Enabled</span>
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-700">
                <button type="button" onClick={() => setModalOpen(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={submitting} className="btn btn-primary">
                  {submitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    editingProvider ? 'Update' : 'Create'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}