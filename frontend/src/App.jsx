import { useState } from 'react';
import { useAuth } from './contexts/AuthContext';
import UploadPage from './pages/UploadPage';
import ChatPage from './pages/ChatPage';
import LoginPage from './pages/LoginPage';

function App() {
  const { user, loading } = useAuth();
  const [currentPage, setCurrentPage] = useState('upload');
  const [uploadedImage, setUploadedImage] = useState(null);
  const [initialPrompt, setInitialPrompt] = useState("");
  const [sessionData, setSessionData] = useState(null);
  const [isTransitioning, setIsTransitioning] = useState(false);

  if (loading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-light-bg dark:bg-dark-bg">
        <div className="text-light-text dark:text-dark-text">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  const handleUploadComplete = (image, prompt, response) => {
    setUploadedImage(image);
    setInitialPrompt(prompt);
    setSessionData(response);
    setIsTransitioning(true);

    // Start transition
    setTimeout(() => {
      setCurrentPage('chat');
      
    }, 500);
  };

  const handleNewChat = () => {
    setIsTransitioning(true);
    setTimeout(() => {
      setCurrentPage('upload');
      setUploadedImage(null);
      setInitialPrompt('');
      setSessionData(null);
      setIsTransitioning(false);
    }, 500);
  };

  const handleLoadSession = async (session) => {
    setInitialPrompt(session.initialPrompt);
    setSessionData(session);
    setUploadedImage(null); // Will be loaded separately in ChatPage
    setIsTransitioning(true);
    
    setTimeout(() => {
      setCurrentPage('chat');
    }, 500);
  };

  return (
    <div className="h-screen w-screen bg-light-bg dark:bg-dark-bg text-light-text dark:text-dark-text font-sans">
      {currentPage === 'upload' && (
        <div 
          className={`h-full w-full transition-all duration-500 ease-in-out ${isTransitioning ? 'opacity-0 translate-y-[-20px]' : 'opacity-100 translate-y-0'}`}
        >
          <UploadPage 
            onUploadComplete={handleUploadComplete} 
            onLoadSession={handleLoadSession}
          />
        </div>
      )}
      
      {currentPage === 'chat' && (
         <div className="transition-all duration-500 ease-in-out opacity-0 animate-fade-slide-in">
          <ChatPage 
            uploadedImage={uploadedImage} 
            initialPrompt={initialPrompt} 
            sessionData={sessionData}
            onNewChat={handleNewChat}
            onLoadSession={handleLoadSession}
          />
        </div>
      )}
    </div>
  );
}

export default App;
