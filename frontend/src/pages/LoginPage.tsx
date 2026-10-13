import { useAuth } from '../hooks';
import { Server, Shield, Zap, ArrowRight } from 'lucide-react';
import { useState } from 'react';
import toast from 'react-hot-toast';

export function LoginPage() {
  const { login, demoLogin, loading } = useAuth();
  const [demoLoading, setDemoLoading] = useState(false);

  const handleLogin = async () => {
    try {
      await login();
    } catch {
      toast.error('Failed to initiate login');
    }
  };

  const handleDemoLogin = async () => {
    setDemoLoading(true);
    try {
      await demoLogin();
      toast.success('Demo login successful');
    } catch {
      toast.error('Demo login failed');
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-slate-50 dark:bg-slate-900">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-100 dark:bg-blue-900 mb-4">
            <Server className="w-8 h-8 text-blue-700 dark:text-blue-300" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Sentinel Foundry</h1>
          <p className="mt-2 text-slate-600 dark:text-slate-400">
            Multi-provider AI proxy for developer tools
          </p>
        </div>

        <div className="space-y-4">
          <button
            onClick={handleLogin}
            disabled={loading}
            className="w-full btn btn-primary btn-lg gap-3"
          >
            <Shield className="w-5 h-5" />
            <span>Sign in with Keycloak</span>
            <ArrowRight className="w-5 h-5 ml-auto" />
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200 dark:border-slate-700" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-slate-50 dark:bg-slate-900 text-slate-500 dark:text-slate-400">
                Or continue with demo
              </span>
            </div>
          </div>

          <button
            onClick={handleDemoLogin}
            disabled={demoLoading}
            className="w-full btn btn-secondary btn-lg gap-3"
          >
            <Zap className="w-5 h-5" />
            <span>{demoLoading ? 'Signing in...' : 'Demo Mode'}</span>
          </button>
        </div>

        <div className="mt-8 p-4 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
          <h3 className="text-sm font-medium text-slate-900 dark:text-white mb-2">Demo Mode</h3>
          <ul className="text-sm text-slate-600 dark:text-slate-400 space-y-1">
            <li>• Pre-configured with sample providers</li>
            <li>• Full dashboard access with operator role</li>
            <li>• Data persists in SQLite database</li>
            <li>• Not available in production</li>
          </ul>
        </div>

        <p className="mt-6 text-center text-xs text-slate-500 dark:text-slate-400">
          Sentinel Foundry v1.0.0 — Alan Vo | AI & Machine Learning
        </p>
      </div>
    </div>
  );
}