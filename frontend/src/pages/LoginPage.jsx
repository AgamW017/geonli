import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';

export default function LoginPage({ onBack }) {
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login, signup } = useAuth();
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


  return (
    <div className="min-h-screen flex items-center justify-center bg-light-bg dark:bg-dark-bg">
      <div className="w-full max-w-sm m-5 p-8 rounded-[30px] bg-white dark:bg-dark-panel shadow-[0_15px_30px_-20px_rgba(133,189,215,0.88)] dark:shadow-[0_20px_35px_-20px_rgba(80,160,220,0.35)] border border-white dark:border-[rgba(80,160,220,0.25)]">
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
          <div className="flex gap-2">
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

        <h2 className="text-3xl font-bold text-center mt-8 mb-6 text-light-text dark:text-dark-text">
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
              className="w-full px-4 py-2 rounded-l border bg-light-bg dark:bg-dark-bg border-light-border dark:border-[rgba(80,160,220,0.25)] text-light-text dark:text-dark-text shadow-[0_5px_10px_-5px_#cff0ff] dark:shadow-[0_6px_12px_-6px_rgba(80,160,220,0.35)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
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
              className="w-full px-4 py-2 rounded-l border bg-light-bg dark:bg-dark-bg border-light-border dark:border-[rgba(80,160,220,0.25)] text-light-text dark:text-dark-text shadow-[0_5px_10px_-5px_#cff0ff] dark:shadow-[0_6px_12px_-6px_rgba(80,160,220,0.35)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className={`w-full py-2 px-4 rounded-l font-medium transition-all shadow-[0_15px_10px_-15px_rgba(133,189,215,0.88)] dark:shadow-[0_18px_12px_-14px_rgba(80,160,220,0.35)] ${
              loading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-[var(--color-secondary)] hover:opacity-90 active:scale-95' 
            } text-white`}
            style={{ marginTop: '1.5rem' }}
          >
            {loading ? 'Loading...' : (isSignup ? 'Sign Up' : 'Log In')}
          </button>
        </form>
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
