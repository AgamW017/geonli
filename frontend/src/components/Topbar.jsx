import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';

function Topbar({ onShowLogin }) {
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();

  return (
    <header className="flex-shrink-0 flex items-center justify-between h-12 px-4 sm:px-6 border-b border-light-border dark:border-dark-border">
      <h1 className="text-xl font-semibold">GeoNLI</h1>
      
      <div className="flex items-center gap-4">
        {/* User Info or Login Button */}
        {user ? (
          <div className="flex items-center gap-2">
            <span className="text-sm text-light-text-dim dark:text-dark-text-dim">
              {user.email}
            </span>
            <button
              onClick={logout}
              className="px-3 py-1 text-sm rounded-md bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-colors"
            >
              Logout
            </button>
          </div>
        ) : (
          <button
            onClick={onShowLogin}
            className="px-4 py-1.5 text-sm rounded-md bg-blue-500 text-white hover:bg-blue-600 transition-colors font-medium"
          >
            Login
          </button>
        )}
        
        {/* Theme Toggle */}
        <div className="flex items-center space-x-2">
          <span className="text-sm text-light-text-dim dark:text-dark-text-dim">Theme</span>
          <div className="flex items-center p-1 rounded-full bg-light-bg dark:bg-dark-bg border border-light-border dark:border-dark-border">
            <button
              onClick={() => toggleTheme('light')}
              className={`p-1 px-3 rounded-full text-sm ${theme === 'light' ? 'bg-white dark:bg-gray-700' : 'text-light-text-dim dark:text-dark-text-dim'}`}
            >
              Light
            </button>
            <button
              onClick={() => toggleTheme('dark')}
              className={`p-1 px-3 rounded-full text-sm ${theme === 'dark' ? 'bg-black text-white' : 'text-light-text-dim dark:text-dark-text-dim'}`}
            >
              Dark
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Topbar;
