import { useState, useEffect } from 'react';
import { useSessions } from '../hooks';
import { useNavigate } from 'react-router-dom';
import { Plus, Edit, Trash2, Download, Search, Loader2, MessageSquare, X } from 'lucide-react';
import { Session, SessionCreate } from '../types';
import { formatRelativeTime } from '../utils/format';

export function SessionsPage() {
  const { sessions, loading, pagination, fetchSessions, createSession, updateSession, deleteSession, exportSession } = useSessions();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSession, setEditingSession] = useState<Session | null>(null);
  const [formData, setFormData] = useState<SessionCreate>({
    title: '',
    model: '',
    provider_id: '',
    metadata: {},
  });
  const [submitting, setSubmitting] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [exporting, setExporting] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    fetchSessions(page);
  }, [fetchSessions, page]);

  const handleOpenCreate = () => {
    setEditingSession(null);
    setFormData({ title: '', model: '', provider_id: '', metadata: {} });
    setModalOpen(true);
  };

  const handleOpenEdit = (session: Session) => {
    setEditingSession(session);
    setFormData({ title: session.title || '', model: session.model || '', provider_id: session.provider_id || '', metadata: session.metadata || {} });
    setModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (editingSession) {
        await updateSession(editingSession.id, formData);
      } else {
        const newSession = await createSession(formData);
        if (newSession) {
          navigate(`/sessions/${newSession.id}`);
        }
      }
      setModalOpen(false);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (session: Session) => {
    if (!confirm(`Delete session "${session.title || 'Untitled'}"? This cannot be undone.`)) return;
    setDeleting(session.id);
    try {
      await deleteSession(session.id);
    } finally {
      setDeleting(null);
    }
  };

  const handleExport = async (id: string) => {
    setExporting(id);
    try {
      await exportSession(id);
    } finally {
      setExporting(null);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    if (type === 'checkbox') {
      setFormData(prev => ({ ...prev, [name]: (e.target as HTMLInputElement).checked }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  const filteredSessions = sessions.filter(s =>
    (s.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Sessions</h1>
          <p className="text-slate-600 dark:text-slate-400 mt-1">
            Manage conversation history
          </p>
        </div>
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search sessions..."
              className="input pl-10"
            />
          </div>
          <button onClick={handleOpenCreate} className="btn btn-primary gap-2 whitespace-nowrap">
            <Plus className="w-4 h-4" />
            New Session
          </button>
        </div>
      </div>

      <div className="card">
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th className="w-8"></th>
                <th>Title</th>
                <th>Model</th>
                <th>Messages</th>
                <th>Updated</th>
                <th className="w-48">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && sessions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <div className="spinner" />
                      <p className="text-slate-500 dark:text-slate-400">Loading sessions...</p>
                    </div>
                  </td>
                </tr>
              ) : filteredSessions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center">
                    <div className="empty-state">
                      <MessageSquare className="w-12 h-12" />
                      <h3>{searchQuery ? 'No matching sessions' : 'No sessions yet'}</h3>
                      <p>{searchQuery ? 'Try a different search term' : 'Create your first session to get started'}</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredSessions.map((session) => (
                  <tr key={session.id}>
                    <td>
                      <button
                        onClick={() => navigate(`/sessions/${session.id}`)}
                        className="btn btn-ghost btn-sm p-1.5"
                        aria-label={`Open session ${session.title || session.id}`}
                      >
                        <MessageSquare className="w-4 h-4" />
                      </button>
                    </td>
                    <td>
                      <div>
                        <p className="font-medium text-slate-900 dark:text-white truncate max-w-md">
                          {session.title || 'Untitled Session'}
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400 font-mono">{session.id.slice(0, 8)}...</p>
                      </div>
                    </td>
                    <td className="font-mono text-sm text-slate-600 dark:text-slate-400">
                      {session.model || '—'}
                    </td>
                    <td className="text-slate-600 dark:text-slate-400">{session.message_count}</td>
                    <td className="text-sm text-slate-500 dark:text-slate-400">{formatRelativeTime(session.updated_at)}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleOpenEdit(session)}
                          className="btn btn-ghost btn-sm p-1.5"
                          aria-label={`Edit ${session.title || session.id}`}
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleExport(session.id)}
                          disabled={exporting === session.id}
                          className="btn btn-ghost btn-sm p-1.5"
                          aria-label={`Export ${session.title || session.id}`}
                        >
                          {exporting === session.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                        </button>
                        <button
                          onClick={() => handleDelete(session)}
                          disabled={deleting === session.id}
                          className="btn btn-ghost btn-sm p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                          aria-label={`Delete ${session.title || session.id}`}
                        >
                          {deleting === session.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
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
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow-xl w-full max-w-md" onClick={e => e.stopPropagation()}>
            <div className="p-5 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                {editingSession ? 'Edit Session' : 'New Session'}
              </h2>
              <button onClick={() => setModalOpen(false)} className="btn btn-ghost p-1.5">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-5 space-y-4">
              <div>
                <label htmlFor="title" className="label">Title (optional)</label>
                <input
                  id="title"
                  name="title"
                  type="text"
                  value={formData.title}
                  onChange={handleChange}
                  className="input"
                  placeholder="My coding session"
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

              <div>
                <label htmlFor="provider_id" className="label">Provider ID (optional)</label>
                <input
                  id="provider_id"
                  name="provider_id"
                  type="text"
                  value={formData.provider_id}
                  onChange={handleChange}
                  className="input"
                  placeholder="provider-uuid"
                />
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
                    editingSession ? 'Update' : 'Create'
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