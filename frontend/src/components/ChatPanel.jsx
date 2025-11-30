import { useState, useRef, useEffect } from 'react';
import { MessageSquareIcon, SendIcon } from './icons';
import { api } from '../services/api';

function ChatPanel({ initialPrompt, sessionData, onMessageSent, onOverlaysUpdate }) {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [loadingHistory, setLoadingHistory] = useState(false);
    const chatEndRef = useRef(null);
    const currentSessionId = useRef(null);

    // Load chat history when session changes
    useEffect(() => {
        const loadChatHistory = async () => {
            if (!sessionData?.sessionId) return;
            
            // Check if this is a new session or we're switching sessions
            if (currentSessionId.current !== sessionData.sessionId) {
                currentSessionId.current = sessionData.sessionId;
                
                // If sessionData already has messages, use them instead of fetching
                if (sessionData.messages && sessionData.messages.length > 0) {
                    setMessages(sessionData.messages);
                } else {
                    setLoadingHistory(true);
                    try {
                        // Try to load existing chat history
                        const response = await api.getChatHistory(sessionData.sessionId);
                        if (response.messages && response.messages.length > 0) {
                            setMessages(response.messages);
                        } else {
                            // New session - show initial messages
                            const userMsg = { id: crypto.randomUUID(), from: 'user', text: initialPrompt || 'Image uploaded' };
                            const aiMsg = { 
                                id: crypto.randomUUID(), 
                                from: 'ai', 
                                text: sessionData.initialResponse || 'Image uploaded successfully!' 
                            };
                            setMessages([userMsg, aiMsg]);
                        }
                    } catch (err) {
                        console.error('Failed to load chat history:', err);
                        // Fall back to initial messages
                        if (initialPrompt) {
                            const userMsg = { id: crypto.randomUUID(), from: 'user', text: initialPrompt };
                            const aiMsg = { 
                                id: crypto.randomUUID(), 
                                from: 'ai', 
                                text: sessionData.initialResponse || 'Image uploaded successfully!' 
                            };
                            setMessages([userMsg, aiMsg]);
                        }
                    } finally {
                        setLoadingHistory(false);
                    }
                }
            }
        };

        loadChatHistory();
    }, [sessionData, initialPrompt]);

    // Scroll to bottom
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim() || !sessionData?.sessionId) return;
        
        const userMessage = { id: crypto.randomUUID(), from: 'user', text: input };
        const thinkingMessage = { id: 'thinking-temp', from: 'ai', text: 'Thinking...', isThinking: true };
        setMessages(prev => [...prev, userMessage, thinkingMessage]);
        setInput('');
        setLoading(true);

        try {
            const response = await api.sendMessage(
                sessionData.sessionId, 
                input,
                sessionData.imageUrl
            );
            
            // Remove thinking message and add real response
            setMessages(prev => {
                const filtered = prev.filter(msg => msg.id !== 'thinking-temp');
                const aiMessage = { 
                    id: crypto.randomUUID(), 
                    from: 'ai', 
                    text: response.message || response.response 
                };
                return [...filtered, aiMessage];
            });
            
            // If backend sent overlays, update them in parent
            if (response?.overlays && response.overlays.length > 0 && onOverlaysUpdate) {
                onOverlaysUpdate(response.overlays);
            }

            if (onMessageSent) {
                onMessageSent(sessionData.sessionId);
            }
        } catch (err) {
            console.error('Send message error:', err);
            // Remove thinking message and add error
            setMessages(prev => {
                const filtered = prev.filter(msg => msg.id !== 'thinking-temp');
                const errorMessage = { 
                    id: crypto.randomUUID(), 
                    from: 'ai', 
                    text: 'Sorry, there was an error processing your message.' 
                };
                return [...filtered, errorMessage];
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <aside className="flex flex-col h-full border-l border-light-border dark:border-dark-border transition-all duration-300 ease-in-out bg-light-panel dark:bg-dark-panel w-96 flex-shrink-0">
            {/* Chat Header */}
            <div className="flex items-center justify-end h-16 px-4 border-b border-light-border dark:border-dark-border flex-shrink-0">
            </div>
            
            {/* Chat Messages */}
            <div className="flex-1 p-4 space-y-4 overflow-y-auto">
                {loadingHistory ? (
                    <div className="flex items-center justify-center h-full">
                        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    </div>
                ) : messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center text-light-text-dim dark:text-dark-text-dim">
                        <MessageSquareIcon className="w-12 h-12 mb-2" />
                        <p>Ask a question about the image to get started.</p>
                    </div>
                ) : null}
                {messages.map(msg => (
                    <div key={msg.id} className={`flex ${msg.from === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`p-3 rounded-lg max-w-[80%]
                            ${msg.from === 'user' 
                                ? 'text-white bg-[var(--color-accent)]' 
                                : 'bg-light-bg dark:bg-dark-bg'
                            }
                        `}>
                            {msg.isThinking ? (
                                <div className="flex items-center gap-2">
                                    <div className="flex gap-1">
                                        <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                                        <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                                        <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                                    </div>
                                    <p className="text-light-text-dim dark:text-dark-text-dim italic">{msg.text}</p>
                                </div>
                            ) : (
                                <p>{msg.text}</p>
                            )}
                        </div>
                    </div>
                ))}
                <div ref={chatEndRef} />
            </div>
            
            {/* Chat Input */}
            <div className="p-4 border-t border-light-border dark:border-dark-border">
                <form onSubmit={handleSubmit} className="relative">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask a follow-up..."
                        className="w-full pl-4 pr-12 py-3 rounded-full bg-light-bg dark:bg-dark-bg border border-light-border dark:border-dark-border focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                    />
                    <button
                        type="submit"
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full text-white bg-[var(--color-accent)] hover:opacity-90 disabled:bg-gray-400"
                        disabled={!input.trim() || loading}
                    >
                        {loading ? (
                            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        ) : (
                            <SendIcon className="w-5 h-5" />
                        )}
                    </button>
                </form>
            </div>
        </aside>
    );
}

export default ChatPanel;
