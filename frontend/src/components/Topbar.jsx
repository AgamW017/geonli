import { useTheme } from '../contexts/ThemeContext';
import logo from '../assets/logo.png';

function Topbar() {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="flex-shrink-0 flex items-center justify-between h-14 px-4 sm:px-6 border-b border-light-border dark:border-dark-border">
      <div className="flex items-center gap-3">
        <img src={logo} alt="Logo" className="w-15 h-12 rounded-md object-contain" />
        <div className="leading-tight">
          <h1 className="text-xl font-bold">GeoNLI Image Chat</h1>
          <p className="text-xs text-light-text-dim dark:text-dark-text-dim">
            Describe and reason about satellite imagery with a conversational interface.
          </p>
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        {/* Theme Toggle */}
        <div className="flex items-center space-x-2">
          <span className="text-sm text-light-text-dim dark:text-dark-text-dim">Theme</span>
          <div className="flex items-center p-1 rounded-full bg-light-bg dark:bg-dark-bg border border-light-border dark:border-dark-border">
            <button
              onClick={() => toggleTheme('light')}
              className={`p-1 px-3 rounded-full text-sm ${theme === 'light' ? 'bg-[var(--color-accent)] text-white' : 'text-light-text-dim dark:text-dark-text-dim'}`}
            >
              Light
            </button>
            <button
              onClick={() => toggleTheme('dark')}
              className={`p-1 px-3 rounded-full text-sm ${theme === 'dark' ? 'bg-[var(--color-accent)] text-white' : 'text-light-text-dim dark:text-dark-text-dim'}`}
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
