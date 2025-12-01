import { useState, useRef } from 'react';
import { UploadCloudIcon, SendIcon } from '../components/icons';
import { api } from '../services/api';
import LeftSidebar from '../components/LeftSidebar';
import Topbar from '../components/Topbar';

function UploadPage({ onUploadComplete, onLoadSession, onShowLogin }) {
  const [prompt, setPrompt] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const fileInputRef = useRef(null);

  const handleFile = (file) => {
    if (file && file.type.startsWith('image/')) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setImageUrl(e.target.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleFileChange = (e) => {
    handleFile(e.target.files[0]);
  };
  
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!imageFile) return;

    setUploading(true);
    setError('');

    try {
      const response = await api.uploadImage(imageFile, prompt);
      onUploadComplete(imageUrl, prompt, response);
    } catch (err) {
      setError(err.response?.data?.message || 'Upload failed. Please try again.');
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden">
      {/* Left Sidebar */}
      <LeftSidebar 
        isOpen={isSidebarOpen} 
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        onNewChat={() => {
          setImageFile(null);
          setImageUrl(null);
          setPrompt('');
          setError('');
        }}
        onLoadSession={onLoadSession}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full">
        <Topbar onShowLogin={onShowLogin} />
        
        <main className="flex-1 flex flex-col items-center justify-center p-4 overflow-y-auto">
          <div className="w-full max-w-2xl flex flex-col items-center">
            <h1 className="text-4xl font-bold mb-8 text-light-text dark:text-dark-text">
              Start a new chat
            </h1>

            {error && (
              <div className="w-full mb-4 p-3 bg-red-500/10 border border-red-500 rounded-md">
                <p className="text-red-500 text-sm">{error}</p>
              </div>
            )}

        {/* Drop zone */}
        <div
          className={`relative flex flex-col items-center justify-center w-full h-64 rounded-2xl border-2 border-dashed
            ${isDragging ? 'border-[var(--color-accent)] bg-[var(--color-accent)]/10' : 'border-light-border dark:border-dark-border'}
            ${imageUrl ? 'border-none' : ''}
            transition-all duration-300 ease-in-out cursor-pointer`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {imageUrl ? (
            <img 
              src={imageUrl} 
              alt="Uploaded preview" 
              className="object-contain h-full w-full rounded-2xl" 
            />
          ) : (
            <div className="text-center text-light-text-dim dark:text-dark-text-dim">
              <UploadCloudIcon className="w-12 h-12 mx-auto mb-2" />
              <p className="font-medium">
                {isDragging ? 'Drop image here' : 'Drag & drop image or click to upload'}
              </p>
              <p className="text-sm">JPEG or PNG</p>
            </div>
          )}
        </div>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          className="hidden"
          accept="image/jpeg, image/png"
        />

        {/* Prompt Input */}
        <form onSubmit={handleSubmit} className="w-full mt-6">
          <div className="relative">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ask anything..."
              className="w-full pl-4 pr-12 py-4 rounded-full bg-light-panel dark:bg-dark-panel border border-light-border dark:border-dark-border focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] transition-all"
            />
            <button
              type="submit"
              disabled={!imageFile || uploading}
              className={`absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full transition-colors
                ${imageFile && !uploading ? 'bg-[var(--color-secondary)] text-white hover:opacity-90' : 'bg-light-bg dark:bg-dark-bg text-light-text-dim dark:text-dark-text-dim cursor-not-allowed'}`}
            >
              {uploading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <SendIcon className="w-5 h-5" />
              )}
            </button>
          </div>
        </form>
          </div>
        </main>
      </div>
    </div>
  );
}

export default UploadPage;
