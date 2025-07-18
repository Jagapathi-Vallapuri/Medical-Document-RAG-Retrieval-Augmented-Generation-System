import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ApiService } from '../services/ApiService';
import { markdownToHtml } from '../utils/markdown.js';

const apiService = new ApiService();

// Constants for consistent messaging
const INITIAL_MESSAGES = {
    welcome: 'Hello! I\'m your AI assistant. Please select a document from the sidebar, then ask me any questions about it. How can I assist you today?',
    documentSelected: (docName) => `You have selected: **${docName}**. Ask me anything about this document.`,
    noDocumentSelected: 'Please select at least one document from the sidebar before asking questions.'
};

// Helper function to create unique message IDs
const generateMessageId = () => `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

// Enhanced error handling
const getErrorMessage = (error) => {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
        return 'Network connection issue. Please check your internet connection and try again.';
    }
    if (error.status === 500) {
        return 'Server error. Our team has been notified. Please try again in a few moments.';
    }
    if (error.status === 413) {
        return 'Your message or document is too large. Please try with a shorter message.';
    }
    if (error.status === 404) {
        return 'The requested service is unavailable. Please try again later.';
    }
    return 'I apologize, but I encountered an unexpected issue. Please try again.';
};

const Message = React.memo(({ message }) => {
    const formattedContent = markdownToHtml(message.content);

    return (
        <div className={`message ${message.type}`} role="article" aria-label={`${message.type === 'user' ? 'Your' : 'AI'} message`}>
            <div className="message-avatar">
                <div className={`${message.type}-avatar`}>{message.type === 'user' ? 'You' : 'AI'}</div>
            </div>
            <div className="message-content">
                <div 
                    className="message-text" 
                    dangerouslySetInnerHTML={{ __html: formattedContent }}
                ></div>
                <div className="message-time">{new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
            </div>
        </div>
    );
});

Message.displayName = 'Message';

const TypingIndicator = () => (
    <div className="message assistant" role="status" aria-label="AI is typing">
        <div className="message-avatar">
            <div className="assistant-avatar">AI</div>
        </div>
        <div className="message-content">
            <div className="typing-indicator">
                <span className="typing-text">AI is thinking</span>
                <div className="typing-dots">
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                </div>
            </div>
        </div>
    </div>
);

TypingIndicator.displayName = 'TypingIndicator';

export const ChatInterface = ({ selectedDocs, onLoadingChange }) => {
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const textareaRef = useRef(null);
    const messagesEndRef = useRef(null);

    // Helper function to create initial message
    const createInitialMessage = useCallback(() => ({
        id: generateMessageId(),
        type: 'assistant',
        content: selectedDocs && selectedDocs.length > 0
            ? INITIAL_MESSAGES.documentSelected(selectedDocs[0])
            : INITIAL_MESSAGES.welcome,
        timestamp: new Date()
    }), [selectedDocs]);

    useEffect(() => {
        setMessages([createInitialMessage()]);
        setInputValue('');
        setIsTyping(false);
    }, [selectedDocs, createInitialMessage]);


    useEffect(() => {
        const scrollToBottom = () => {
            messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        };
        
        const timeoutId = setTimeout(scrollToBottom, 100);
        
        return () => clearTimeout(timeoutId);
    }, [messages, isTyping]);

    const autoResize = () => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px';
        }
    };

    const handleInputChange = (e) => {
        setInputValue(e.target.value);
        autoResize();
    };

    const sendMessage = useCallback(async () => {
        const messageText = inputValue.trim();
        if (!messageText || isTyping) return;

        if (!selectedDocs || selectedDocs.length === 0) {
            setMessages(prev => [...prev, {
                id: generateMessageId(),
                type: 'assistant',
                content: INITIAL_MESSAGES.noDocumentSelected,
                timestamp: new Date()
            }]);
            return;
        }

        const userMessage = {
            id: generateMessageId(),
            type: 'user',
            content: messageText,
            timestamp: new Date()
        };
        setMessages(prev => [...prev, userMessage]);
        setInputValue('');
        setTimeout(autoResize, 0);
        setIsTyping(true);
        if (onLoadingChange) onLoadingChange(true);

        try {
            const response = await apiService.sendMessage(messageText, selectedDocs);
            const assistantMessage = {
                id: generateMessageId(),
                type: 'assistant',
                content: response.message || response.response || 'I apologize, but I encountered an issue processing your request.',
                timestamp: new Date()
            };
            setMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            console.error('Error sending message:', error);
            const errorMessage = {
                id: generateMessageId(),
                type: 'assistant',
                content: getErrorMessage(error),
                timestamp: new Date()
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsTyping(false);
            if (onLoadingChange) onLoadingChange(false);
        }
    }, [inputValue, isTyping, selectedDocs, onLoadingChange]);

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    const handleResetChat = useCallback(() => {
        setMessages([createInitialMessage()]);
        setInputValue('');
        setIsTyping(false);
    }, [createInitialMessage]);

    return (
        <div className="chat-interface">
            <div className="chat-header">
                <div className="chat-title-section">
                    <h4>AI Assistant</h4>
                    {selectedDocs && selectedDocs.length > 0 && (
                        <div className="chat-status">
                            <div className="status-indicator"></div>
                            <span>{selectedDocs.length} document{selectedDocs.length !== 1 ? 's' : ''} selected</span>
                        </div>
                    )}
                </div>
                <button 
                    className="btn-secondary" 
                    onClick={handleResetChat}
                    aria-label="Start a new chat conversation"
                    type="button"
                >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                        <polyline points="1,4 1,10 7,10"/>
                        <path d="M3.51,15a9,9,0,0,0,13.48-12.76"/>
                    </svg>
                    New Chat
                </button>
            </div>
            <div className="chat-messages" role="log" aria-live="polite" aria-label="Chat conversation">
                {messages.map((msg) => <Message key={msg.id} message={msg} />)}
                {isTyping && <TypingIndicator />}
                <div ref={messagesEndRef} />
            </div>
            <div className="chat-input-container">
                <div className="chat-input-wrapper">
                    <textarea
                        ref={textareaRef}
                        className="chat-input"
                        placeholder={selectedDocs && selectedDocs.length > 0 
                            ? "Ask me anything about your documents..." 
                            : "Select documents to start asking questions..."}
                        rows="1"
                        value={inputValue}
                        onChange={handleInputChange}
                        onKeyDown={handleKeyDown}
                        aria-label="Chat message input"
                        aria-describedby="input-hint"
                        role="textbox"
                        aria-multiline="true"
                        disabled={!selectedDocs || selectedDocs.length === 0}
                    />
                    <button 
                        className="send-btn" 
                        onClick={sendMessage} 
                        disabled={!inputValue.trim() || isTyping || !selectedDocs || selectedDocs.length === 0}
                        aria-label={isTyping ? "Sending message..." : "Send message"}
                        aria-describedby="input-hint"
                        type="button"
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                            <line x1="22" y1="2" x2="11" y2="13"/>
                            <polygon points="22,2 15,22 11,13 2,9 22,2"/>
                        </svg>
                    </button>
                </div>
                <div className="input-hint" id="input-hint">
                    Press Enter to send, Shift+Enter for new line
                </div>
            </div>
        </div>
    );
};