import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSessions } from '../hooks';
import { ArrowLeft, Edit, Trash2, Download, Loader2, Send, Copy, Check } from 'lucide-react';
import { Session, MessageCreate } from '../types';
import { formatRelativeTime, cn } from '../utils/format';
import toast from 'react-hot-toast';

export function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { getSession, addMessage, updateSession, deleteSession, exportSession, loading: sessionsLoading } = useSessions();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [newMessage, setNewMessage] = useState('');
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleInput, setTitleInput] = useState('');
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      loadSession();
    }
  }, [id]);

  const loadSession = async () => {
    setLoading(true);
    try {
      const data = await getSession(id!);
      if (data) {
        setSession(data);
        if (data.title) setTitleInput(data.title);
      } else {
        navigate('/sessions');
      }
    } catch {
      navigate('/sessions');
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !session) return;
    setSending(true);
    try {
      const message: MessageCreate = {
        role: 'user',
        content: newMessage.trim(),
      };
      await addMessage(session.id, message);
      setNewMessage('');
      await loadSession();
    } catch {
      toast.error('Failed to send message');
    } finally {
      setSending(false);
    }
  };

  const handleUpdateTitle = async () => {
    if (!session) return;
    try {
      await updateSession(session.id, { title: titleInput });
      setEditingTitle(false);
      toast.success('Title updated');
    } catch {
      toast.error('Failed to update title');
    }
  };

  const handleDelete = async () => {
    if (!session) return;
    if (!confirm(`Delete session "${session.title || 'Untitled'}"? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await deleteSession(session.id);
      navigate('/sessions');
    } finally {
      setDeleting(false);
    }
  };

  const handleExport = async () => {
    if (!session) return;
    setExporting(true);
    try {
      await exportSession(session.id);
    } finally {
      setExporting(false);
    }
  };

  const handleCopyId = (msgId: string) => {
    navigator.clipboard.writeText(msgId);
    setCopiedId(msgId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (loading || sessionsLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <div className="spinner" />
      </div>
    );
  }

  if (!session) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500 dark:text-slate-400">Session not found</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/sessions')} className="btn btn-ghost p-2" aria-label="Back to sessions">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            {editingTitle ? (
              <input
                type="text"
                value={titleInput}
                onChange={e => setTitleInput(e.target.value)}
                onBlur={handleUpdateTitle}
                onKeyDown={e => e.key === 'Enter' && handleUpdateTitle()}
                className="input text-lg font-medium w-64"
                autoFocus
              />
            ) : (
              <h1 className="text-xl font-semibold text-slate-900 dark:text-white truncate max-w-xl flex items-center gap-2">
                {session.title || 'Untitled Session'}
                <button
                  onClick={() => { setEditingTitle(true); setTitleInput(session.title || ''); }}
                  className="btn btn-ghost p-1 opacity-0 group-hover:opacity-100"
                  aria-label="Edit title"
                >
                  <Edit className="w-4 h-4" />
                </button>
              </h1>
            )}
            <p className="text-sm text-slate-500 dark:text-slate-400 font-mono">{session.id}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleExport} disabled={exporting} className="btn btn-secondary btn-sm gap-2">
            {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            Export
          </button>
          <button onClick={handleDelete} disabled={deleting} className="btn btn-ghost btn-sm p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {session.messages && session.messages.length > 0 ? (
          session.messages.map((message) => (
            <div key={message.id} className={cn('flex gap-3', message.role === 'user' ? 'flex-row-reverse' : '')}>
              <div
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
                  message.role === 'user'
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                    : message.role === 'assistant'
                    ? 'bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                )}
              >
                {message.role === 'user' ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
                )}
              </div>
              <div className={cn('flex-1 min-w-0', message.role === 'user' ? 'text-right' : '')}>
                <div className={cn(
                  'relative max-w-[80%] px-4 py-2.5 rounded-2xl',
                  message.role === 'user'
                    ? 'bg-blue-50 dark:bg-blue-900/30 text-slate-900 dark:text-white ml-auto rounded-br-md'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white mr-auto rounded-bl-md'
                )}>
                  <pre className="whitespace-pre-wrap text-sm">{message.content}</pre>
                  <div className="absolute bottom-1 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => handleCopyId(message.id)}
                      className="btn btn-ghost p-1.5 text-xs"
                      aria-label="Copy message ID"
                    >
                      {copiedId === message.id ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                </div>
                <p className={cn('text-xs text-slate-500 dark:text-slate-400 mt-1', message.role === 'user' ? 'text-right' : '')}>
                  {formatRelativeTime(message.created_at)}
                </p>
              </div>
            </div>
          ))
        ) : (
          <div className="empty-state flex-1">
            <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <h3>No messages yet</h3>
            <p>Send a message to start the conversation</p>
          </div>
        )}

        <form onSubmit={handleSendMessage} className="border-t border-slate-200 dark:border-slate-700 pt-4">
          <div className="flex gap-2">
            <textarea
              value={newMessage}
              onChange={e => setNewMessage(e.target.value)}
              placeholder="Type a message..."
              className="input flex-1 resize-none min-h-[80px] max-h-[200px]"
              rows={3}
              disabled={sending}
            />
            <button
              type="submit"
              disabled={sending || !newMessage.trim()}
              className="btn btn-primary self-end mb-1"
              aria-label="Send message"
            >
              {sending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}