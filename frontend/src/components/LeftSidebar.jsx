import { MenuIcon, PlusIcon, MessageSquareIcon, UserIcon, LogOutIcon } from './icons';
import { useState, useEffect, useImperativeHandle, forwardRef, useRef, useLayoutEffect } from 'react';
import { api } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const LeftSidebar = forwardRef(({ isOpen, onToggleSidebar, onNewChat, onLoadSession, onShowLogin }, ref) => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [openMenuId, setOpenMenuId] = useState(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const sessionRefs = useRef({});
  const prevPositions = useRef({});
  const isAnimating = useRef(false);
  const optionsPopoverRef = useRef(null);
  const { user, logout } = useAuth();

  useEffect(() => {
    loadSessions();
  }, []);

  // Close any open menus/modals on outside click or Escape
  useEffect(() => {
    const onGlobalClick = (e) => {
      // If click happens inside the options popover, do not close
      if (optionsPopoverRef.current && optionsPopoverRef.current.contains(e.target)) {
        return;
      }
      // Close menu on outside click
      if (openMenuId !== null) setOpenMenuId(null);
      // Do not auto-close confirm dialog here; backdrop handles its close
    };
    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (openMenuId !== null) setOpenMenuId(null);
        if (confirmDeleteId !== null) setConfirmDeleteId(null);
      }
    };
    // Use bubble phase so inner handlers can run first
    window.addEventListener('mousedown', onGlobalClick, false);
    window.addEventListener('keydown', onKeyDown, true);
    return () => {
      window.removeEventListener('mousedown', onGlobalClick, false);
      window.removeEventListener('keydown', onKeyDown, true);
    };
  }, [openMenuId, confirmDeleteId]);

  const loadSessions = async () => {
    setLoading(true);
    try {
      const response = await api.getSessions();
      setSessions(response.sessions || []);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setLoading(false);
    }
  };

  // Capture positions before state update
  const capturePositions = () => {
    Object.keys(sessionRefs.current).forEach(sessionId => {
      const element = sessionRefs.current[sessionId];
      if (element) {
        const rect = element.getBoundingClientRect();
        prevPositions.current[sessionId] = rect.top;
      }
    });
  };

  // Apply FLIP animation after positions captured
  useLayoutEffect(() => {
    if (!isAnimating.current) return;

    Object.keys(sessionRefs.current).forEach(sessionId => {
      const element = sessionRefs.current[sessionId];
      if (element && prevPositions.current[sessionId] !== undefined) {
        const currentRect = element.getBoundingClientRect();
        const prevTop = prevPositions.current[sessionId];
        const deltaY = prevTop - currentRect.top;

        if (Math.abs(deltaY) > 1) {
          // Invert: Move element to old position
          element.style.transform = `translateY(${deltaY}px)`;
          element.style.transition = 'none';

          // Force reflow
          requestAnimationFrame(() => {
            // Play: Animate to new position
            element.style.transform = 'translateY(0)';
            element.style.transition = 'transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)';
          });
        }
      }
    });

    isAnimating.current = false;
  }, [sessions]);

  // Optimistically update session timestamp without API call
  const updateSessionTimestamp = (sessionId) => {
    capturePositions();
    isAnimating.current = true;
    
    setSessions(prevSessions => {
      const updatedSessions = prevSessions.map(session => 
        session.sessionId === sessionId 
          ? { ...session, updatedAt: new Date().toISOString() }
          : session
      );
      // Sort by updatedAt, most recent first
      return updatedSessions.sort((a, b) => 
        new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      );
    });
  };

  // Expose methods to parent
  useImperativeHandle(ref, () => ({
    refreshSessions: loadSessions,
    updateSessionTimestamp
  }));

  const handleSessionClick = (session) => {
    if (onLoadSession) {
      onLoadSession(session);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    // Optimistic remove
    setSessions(prev => prev.filter(s => s.sessionId !== sessionId));
    setOpenMenuId(null);
    setConfirmDeleteId(null);
    try {
      await api.deleteSession(sessionId);
      // After successful delete, go to New Chat like logout flow
      if (typeof onNewChat === 'function') {
        onNewChat();
      }
    } catch (err) {
      // Revert if failed: reload list for consistency
      console.error('Failed to delete session:', err);
      await loadSessions();
    }
  };
  return (
    <aside 
      className={`flex flex-col h-full bg-light-panel dark:bg-dark-panel border-r border-light-border dark:border-dark-border transition-all duration-300 ease-in-out overflow-x-hidden
        ${isOpen ? 'w-72' : 'w-20'}`}
    >
      <div className="h-14 flex items-center px-4 border-b border-light-border dark:border-dark-border flex-shrink-0">
        <button 
          onClick={onToggleSidebar} 
          title="Toggle sidebar" 
          className="p-2 rounded-md text-light-text-dim dark:text-dark-text-dim hover:bg-light-bg dark:hover:bg-dark-bg"
        >
          <MenuIcon className="w-6 h-6" />
        </button>
      </div>
      
      <div className="mt-4 px-4 relative">
            <button 
              onClick={onNewChat}
              title="New Chat" 
              className={`flex items-center rounded-lg text-white bg-[var(--color-secondary)] hover:opacity-90 transition-all duration-300 ease-in-out overflow-hidden
                ${isOpen ? 'w-full gap-3 p-3' : 'rounded-full w-11 h-12 p-3'}`}
            >
          <PlusIcon className="w-5 h-5 flex-shrink-0" />
          {isOpen && (
            <span className="font-medium whitespace-nowrap">
              New Chat
            </span>
          )}
        </button>
      </div>
      
      {/* Panel Content */}
      <div className={`flex-1 ${isOpen ? 'p-4' : 'p-4 flex flex-col items-center'} space-y-4 overflow-y-auto overflow-x-hidden`}>
        
        {/* Wrapper for chat history */}
        <div className={`w-full transition-all duration-300 ease-in-out ${isOpen ? 'opacity-100 h-auto' : 'opacity-0 h-0 invisible'}`}>
          <div className="w-full space-y-2">
            <h3 className={`text-sm font-medium text-light-text-dim dark:text-dark-text-dim whitespace-nowrap transition-all duration-200 ease-in-out ${isOpen ? 'opacity-100 delay-100' : 'opacity-0'}`}>
              CHAT HISTORY
            </h3>
            
            {loading ? (
              <div className="flex items-center justify-center p-4">
                <div className="w-6 h-6 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
              </div>
            ) : sessions.length === 0 ? (
              <div className={`flex flex-col items-center justify-center text-center p-4 rounded-lg bg-light-bg dark:bg-dark-bg transition-all duration-300 ease-in-out ${isOpen ? 'h-24 w-full' : 'w-12 h-12'}`}>
                <MessageSquareIcon className={`text-light-text-dim dark:text-dark-text-dim transition-all duration-300 ${isOpen ? 'w-8 h-8 mb-1' : 'w-6 h-6'}`} />
                <p className={`text-sm text-light-text-dim dark:text-dark-text-dim whitespace-nowrap transition-all duration-200 ease-in-out ${isOpen ? 'opacity-100 delay-100' : 'opacity-0 h-0'}`}>
                  No chats yet
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {sessions.map((session) => (
                  <div
                    key={session.sessionId}
                    ref={el => sessionRefs.current[session.sessionId] = el}
                    className="relative w-full"
                  >
                    <button
                      onClick={() => handleSessionClick(session)}
                      className="w-full p-2 rounded-lg bg-light-bg dark:bg-dark-bg hover:bg-light-border dark:hover:bg-dark-border transition-colors duration-200 text-left group"
                    >
                    <div className="flex items-center gap-3">
                      {/* Image Thumbnail */}
                      {session.thumbnail ? (
                        <div className="w-12 h-12 flex-shrink-0 rounded overflow-hidden bg-light-border dark:bg-dark-border">
                          <img 
                            src={session.thumbnail} 
                            alt="Session thumbnail"
                            className="w-full h-full object-cover"
                          />
                        </div>
                      ) : (
                        <div className="w-12 h-12 flex-shrink-0 rounded bg-light-border dark:bg-dark-border flex items-center justify-center">
                          <MessageSquareIcon className="w-6 h-6 text-light-text-dim dark:text-dark-text-dim" />
                        </div>
                      )}
                      
                      {/* Session Info */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-light-text dark:text-dark-text truncate transition-colors">
                          {session.initialPrompt || 'Untitled Chat'}
                        </p>
                        <p className="text-xs text-light-text-dim dark:text-dark-text-dim mt-0.5">
                          {new Date(session.createdAt).toLocaleDateString('en-GB', { 
                            day: '2-digit', 
                            month: '2-digit', 
                            year: 'numeric' 
                          })}
                        </p>
                      </div>
                      {/* Kebab menu trigger */}
                      <div className="ml-auto">
                        <button
                          title="Session options"
                          onClick={(e) => { e.stopPropagation(); setOpenMenuId(openMenuId === session.sessionId ? null : session.sessionId); }}
                          className="p-2 rounded hover:bg-light-border dark:hover:bg-dark-border text-light-text dark:text-dark-text"
                        >
                          {/* Three dots */}
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                            <path d="M6 10a2 2 0 11-4 0 2 2 0 014 0zm6 0a2 2 0 11-4 0 2 2 0 014 0zm6 0a2 2 0 11-4 0 2 2 0 014 0z" />
                          </svg>
                        </button>
                      </div>
                    </div>
                    </button>
                    {/* Options popover */}
                    {openMenuId === session.sessionId && (
                      <div
                        ref={optionsPopoverRef}
                        className="absolute right-2 top-2 z-10 bg-light-bg dark:bg-dark-bg border border-light-border dark:border-dark-border rounded-md shadow-lg"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          className="px-3 py-2 w-32 text-left text-red-600 hover:text-black dark:hover:text-gray-300 rounded-md"
                          onClick={() => setConfirmDeleteId(session.sessionId)}
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      {/* Confirmation Modal */}
      {confirmDeleteId && (
        <div className="fixed inset-0 z-20 flex items-center justify-center">
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/40" onClick={() => setConfirmDeleteId(null)} />
          {/* Dialog */}
          <div className="relative z-30 w-80 rounded-lg bg-light-panel dark:bg-dark-panel border border-light-border dark:border-dark-border p-4 shadow-xl">
            <h4 className="text-sm font-semibold text-light-text dark:text-dark-text mb-2">Delete session?</h4>
            <p className="text-sm text-light-text-dim dark:text-dark-text-dim mb-4">This action is permanent and cannot be undone.</p>
            <div className="flex justify-end gap-2">
              <button
                className="px-3 py-2 rounded-md bg-light-bg dark:bg-dark-bg text-light-text dark:text-dark-text hover:bg-light-border dark:hover:bg-dark-border"
                onClick={() => setConfirmDeleteId(null)}
              >
                Cancel
              </button>
              <button
                className="px-3 py-2 rounded-md bg-red-600 text-white hover:bg-red-700"
                onClick={() => handleDeleteSession(confirmDeleteId)}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Footer: Auth controls at bottom */}
      <div className={`px-4 py-3 border-t border-light-border dark:border-dark-border flex-shrink-0`}
           style={{ marginTop: 'auto' }}>
        {user ? (
          <div className={`h-10 flex items-center ${isOpen ? 'gap-2' : 'justify-center gap-2'}`}>
            {isOpen && (
              <span className="flex-1 min-w-0 text-sm text-light-text-dim dark:text-dark-text-dim truncate">
                {user.email}
              </span>
            )}
            <button
              onClick={logout}
              title="Logout"
              className={`h-11 flex items-center rounded-md text-white bg-[var(--color-secondary)] hover:opacity-90 transition-all duration-300 ease-in-out overflow-hidden
                ${isOpen ? 'px-3 py-1.5 gap-3' : 'rounded-full w-11 p-3'}`}
            >
              <LogOutIcon className="ml-0.5 w-6 h-6 flex-shrink-0" />
              {isOpen && <span className="font-medium whitespace-nowrap">Logout</span>}
            </button>
          </div>
        ) : (
          <div className={`h-10 mb-2 ${isOpen ? 'block' : 'flex'}`}>
            <button
              onClick={onShowLogin}
              title="Login"
              className={`flex items-center rounded-lg text-white bg-[var(--color-accent)] hover:opacity-90 transition-all duration-300 ease-in-out overflow-hidden
                ${isOpen ? 'w-full gap-3 p-3' : 'rounded-full w-11 h-12 p-3'}`}
            >
              <UserIcon className="w-5 h-5 flex-shrink-0" />
              {isOpen && <span className="font-medium whitespace-nowrap">Login</span>}
            </button>
          </div>
        )}
      </div>
    </aside>
  );
});

LeftSidebar.displayName = 'LeftSidebar';

export default LeftSidebar;
