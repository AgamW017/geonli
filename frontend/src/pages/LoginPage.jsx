import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';

export default function LoginPage({ onNavigate, onBack }) {
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login, signup, loginWithGoogle } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isSignup) {
        await signup(email, password);
      } else {
        await login(email, password);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setError('');
    setLoading(true);
    try {
      await loginWithGoogle();
    } catch (err) {
      setError(err.message || 'Google login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-light-bg dark:bg-dark-bg">
      <div className="w-full max-w-md p-8 rounded-lg shadow-lg bg-white dark:bg-dark-panel">
        {/* Back and Theme Toggle */}
        <div className="flex justify-between items-center mb-4">
          {onBack && (
            <button
              onClick={onBack}
              className="text-sm text-light-text-dim dark:text-dark-text-dim hover:text-light-text dark:hover:text-dark-text transition-colors"
            >
              ← Back to Guest Mode
            </button>
          )}
          <div className={`flex items-center space-x-2 ${!onBack ? 'ml-auto' : ''}`}>
            <span className="text-sm text-light-text-dim dark:text-dark-text-dim">Theme</span>
            <div className="flex items-center p-1 rounded-full bg-light-bg dark:bg-dark-bg border border-light-border dark:border-dark-border">
              <button
                onClick={() => toggleTheme('light')}
                className={`p-1 px-3 rounded-full text-sm transition-colors ${theme === 'light' ? 'bg-[var(--color-accent)] text-white' : 'text-light-text-dim dark:text-dark-text-dim'}`}
              >
                Light
              </button>
              <button
                onClick={() => toggleTheme('dark')}
                className={`p-1 px-3 rounded-full text-sm transition-colors ${theme === 'dark' ? 'bg-[var(--color-accent)] text-white' : 'text-light-text-dim dark:text-dark-text-dim'}`}
              >
                Dark
              </button>
            </div>
          </div>
        </div>

        <h2 className="text-3xl font-bold text-center mb-6 text-light-text dark:text-dark-text">
          {isSignup ? 'Create Account' : 'Welcome Back'}
        </h2>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500 rounded-md">
            <p className="text-red-500 text-sm">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block mb-2 text-sm font-medium text-light-text dark:text-dark-text">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-2 rounded-md border bg-light-bg dark:bg-dark-bg border-light-border dark:border-dark-border text-light-text dark:text-dark-text focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
              placeholder="your@email.com"
            />
          </div>

          <div>
            <label className="block mb-2 text-sm font-medium text-light-text dark:text-dark-text">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="w-full px-4 py-2 rounded-md border bg-light-bg dark:bg-dark-bg border-light-border dark:border-dark-border text-light-text dark:text-dark-text focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className={`w-full py-2 px-4 rounded-md font-medium transition-colors ${
              loading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-[var(--color-secondary)] hover:opacity-90'
            } text-white`}
          >
            {loading ? 'Loading...' : (isSignup ? 'Sign Up' : 'Log In')}
          </button>
        </form>

        <div className="mt-4">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-light-border dark:border-dark-border" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white dark:bg-dark-panel text-light-text-dim dark:text-dark-text-dim">
                Or continue with
              </span>
            </div>
          </div>

          <button
            onClick={handleGoogleLogin}
            disabled={loading}
            className="w-full mt-4 py-2 px-4 rounded-md font-medium transition-colors flex items-center justify-center gap-2 bg-light-bg dark:bg-dark-bg hover:bg-gray-200 dark:hover:bg-dark-border text-light-text dark:text-dark-text border border-light-border dark:border-dark-border"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path
                fill="currentColor"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="currentColor"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="currentColor"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="currentColor"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Google
          </button>
        </div>

        <p className="mt-6 text-center text-sm text-light-text-dim dark:text-dark-text-dim">
          {isSignup ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            onClick={() => setIsSignup(!isSignup)}
            className="text-[var(--color-secondary)] hover:underline font-medium"
          >
            {isSignup ? 'Log In' : 'Sign Up'}
          </button>
        </p>
      </div>
    </div>
  );
}
