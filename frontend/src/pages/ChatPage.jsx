import { useState, useRef, useEffect } from 'react';
import LeftSidebar from '../components/LeftSidebar';
import Topbar from '../components/Topbar';
import ImageViewer from '../components/ImageViewer';
import ChatPanel from '../components/ChatPanel';
import { api } from '../services/api';

function ChatPage({ uploadedImage: initialImage, initialPrompt, sessionData, onNewChat, onLoadSession, onShowLogin }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [overlays, setOverlays] = useState(sessionData?.overlays || []);
  const [uploadedImage, setUploadedImage] = useState(initialImage);
  // Track which session the current image belongs to so we know when to refetch
  const [imageSessionId, setImageSessionId] = useState(sessionData?.sessionId || null);
  const [imageLoading, setImageLoading] = useState(false);
  const sidebarRef = useRef(null);

  // If we mount with a freshly uploaded preview, associate it with the session id
  useEffect(() => {
    if (sessionData?.sessionId && uploadedImage && !imageSessionId) {
      setImageSessionId(sessionData.sessionId);
    }
  }, [sessionData?.sessionId, uploadedImage, imageSessionId]);

  // Fetch image whenever switching to a different session that we don't have loaded
  useEffect(() => {
    const loadSessionImage = async () => {
      const targetSessionId = sessionData?.sessionId;
      if (!targetSessionId) return;

      // If we already have an image and it belongs to this session, skip
      if (uploadedImage && imageSessionId === targetSessionId) return;

      setImageLoading(true);
      try {
        const imageData = await api.getSessionImage(targetSessionId);
        setUploadedImage(imageData.imageUrl);
        setOverlays(imageData.overlays || []);
        setImageSessionId(targetSessionId);
      } catch (error) {
        console.error('Failed to load session image:', error);
      } finally {
        setImageLoading(false);
      }
    };
    loadSessionImage();
  }, [sessionData?.sessionId, uploadedImage, imageSessionId]);

  const handleMessageSent = (sessionId) => {
    if (sidebarRef.current) {
      sidebarRef.current.updateSessionTimestamp(sessionId);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden">
      {/* Left Sidebar */}
      <LeftSidebar 
        ref={sidebarRef}
        isOpen={isSidebarOpen} 
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        onNewChat={onNewChat}
        onLoadSession={onLoadSession}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full">
        <Topbar onShowLogin={onShowLogin} />
        <main className="flex-1 flex h-[calc(100%-3rem)] overflow-hidden">
          {imageLoading ? (
            <div className="flex-1 flex items-center justify-center bg-light-panel dark:bg-dark-panel">
              <div className="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <ImageViewer uploadedImage={uploadedImage} overlays={overlays} />
          )}
          <ChatPanel 
            initialPrompt={initialPrompt} 
            sessionData={sessionData}
            onMessageSent={handleMessageSent}
            onOverlaysUpdate={(newOverlays) => setOverlays(newOverlays)}
          />
        </main>
      </div>
    </div>
  );
}

export default ChatPage;
