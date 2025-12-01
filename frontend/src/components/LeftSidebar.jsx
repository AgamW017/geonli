import { MenuIcon, PlusIcon, MessageSquareIcon } from './icons';
import { useState, useEffect, useImperativeHandle, forwardRef, useRef, useLayoutEffect } from 'react';
import { api } from '../services/api';

const LeftSidebar = forwardRef(({ isOpen, onToggleSidebar, onNewChat, onLoadSession }, ref) => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const sessionRefs = useRef({});
  const prevPositions = useRef({});
  const isAnimating = useRef(false);

  useEffect(() => {
    loadSessions();
  }, []);

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
  return (
    <aside 
      className={`flex flex-col h-full bg-light-panel dark:bg-dark-panel border-r border-light-border dark:border-dark-border transition-all duration-300 ease-in-out overflow-x-hidden
        ${isOpen ? 'w-72' : 'w-20'}`}
    >
      <div className="h-12 flex items-center px-4 border-b border-light-border dark:border-dark-border flex-shrink-0">
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
          className={`flex items-center rounded-lg text-white bg-[var(--color-accent)] hover:opacity-90 transition-all duration-300 ease-in-out overflow-hidden
            ${isOpen ? 'w-full gap-3 p-3' : 'rounded-full w-12 h-12 p-3'}`}
        >
          <PlusIcon className="w-6 h-6 flex-shrink-0" />
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
                  <button
                    key={session.sessionId}
                    ref={el => sessionRefs.current[session.sessionId] = el}
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
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </aside>
  );
});

LeftSidebar.displayName = 'LeftSidebar';

export default LeftSidebar;
