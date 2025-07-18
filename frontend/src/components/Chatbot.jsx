import React, { useState, useRef, useEffect } from 'react'
import { Send, Upload, FileText, Bot, User, AlertCircle, CheckCircle, Loader2, RotateCcw, Copy, Check } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeHighlight from 'rehype-highlight'
import rehypeKatex from 'rehype-katex'
import rehypeRaw from 'rehype-raw'
import { chatAPI } from '../services/api'
import ChatSidebar from './ChatSidebar'
import './Chatbot.css'
import 'highlight.js/styles/github.css'
import 'katex/dist/katex.min.css'

// Function to preprocess AI response for better markdown rendering
const preprocessAIResponse = (content) => {
  // Handle common AI response patterns
  let processed = content;
  
  processed = processed.replace(/```(\w+)?\n?([\s\S]*?)```/g, (match, lang, code) => {
    const language = lang || 'text';
    return `\`\`\`${language}\n${code.trim()}\n\`\`\``;
  });
  
  // Fix inline code that might be using backticks incorrectly
  processed = processed.replace(/`([^`\n]+)`/g, '`$1`');
  
  // Handle bullet points that might not use proper markdown
  processed = processed.replace(/^[\s]*[•·▪▫‣⁃]\s+/gm, '- ');
  
  // Handle numbered lists
  processed = processed.replace(/^[\s]*(\d+)[\.\)]\s+/gm, '$1. ');
  
  // Handle bold text patterns
  processed = processed.replace(/\*\*([^*]+)\*\*/g, '**$1**');
  processed = processed.replace(/__([^_]+)__/g, '**$1**');
  
  // Handle italic text patterns
  processed = processed.replace(/\*([^*]+)\*/g, '*$1*');
  processed = processed.replace(/_([^_]+)_/g, '*$1*');
  
  return processed;
};

// Code block component with copy functionality
const CodeBlock = ({ children, className }) => {
  const [copied, setCopied] = useState(false)
  const codeRef = useRef(null)
  
  const handleCopy = async () => {
    if (codeRef.current) {
      try {
        await navigator.clipboard.writeText(codeRef.current.textContent)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      } catch (err) {
        console.error('Failed to copy:', err)
      }
    }
  }
  
  const match = /language-(\w+)/.exec(className || '')
  const language = match ? match[1] : 'text'
  
  return (
    <div className="code-block-container">
      <div className="code-block-header">
        <span className="code-language">{language}</span>
        <button 
          onClick={handleCopy}
          className="copy-button"
          title={copied ? 'Copied!' : 'Copy code'}
        >
          {copied ? <Check size={16} /> : <Copy size={16} />}
        </button>
      </div>
      <pre className="code-block">
        <code ref={codeRef} className={className}>
          {children}
        </code>
      </pre>
    </div>
  )
}

// Component to render message content with markdown support
const MessageContent = ({ content, type }) => {
  // Only render markdown for bot messages, keep user messages as plain text
  if (type === 'bot') {
    const processedContent = preprocessAIResponse(content);
    
    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeHighlight, rehypeKatex, rehypeRaw]}
        components={{
          // Custom components for better styling
          code: ({ node, inline, className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || '')
            return !inline && match ? (
              <CodeBlock className={className}>
                {children}
              </CodeBlock>
            ) : (
              <code className="inline-code" {...props}>
                {children}
              </code>
            )
          },
          blockquote: ({ children }) => (
            <blockquote className="markdown-blockquote">{children}</blockquote>
          ),
          table: ({ children }) => (
            <div className="table-wrapper">
              <table className="markdown-table">{children}</table>
            </div>
          ),
          ul: ({ children }) => <ul className="markdown-list">{children}</ul>,
          ol: ({ children }) => <ol className="markdown-list">{children}</ol>,
          h1: ({ children }) => <h1 className="markdown-h1">{children}</h1>,
          h2: ({ children }) => <h2 className="markdown-h2">{children}</h2>,
          h3: ({ children }) => <h3 className="markdown-h3">{children}</h3>,
          h4: ({ children }) => <h4 className="markdown-h4">{children}</h4>,
          h5: ({ children }) => <h5 className="markdown-h5">{children}</h5>,
          h6: ({ children }) => <h6 className="markdown-h6">{children}</h6>,
          p: ({ children }) => <p className="markdown-p">{children}</p>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" className="markdown-link">
              {children}
            </a>
          ),
        }}
      >
        {processedContent}
      </ReactMarkdown>
    )
  }
  
  return <p>{content}</p>
}

const Chatbot = () => {
  // Chat Management State
  const [currentChatId, setCurrentChatId] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  
  // Messages and Chat State
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: 'Hello! I\'m your AI assistant. You can ask me questions or upload PDF documents for me to analyze.',
      timestamp: new Date()
    }
  ])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [isUploading, setIsUploading] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [error, setError] = useState(null)
  const [showResetConfirm, setShowResetConfirm] = useState(false)
  const [debugInfo, setDebugInfo] = useState(null) // Add debug info state
  
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Initialize component on mount - both chat and uploaded files
  useEffect(() => {
    const initializeComponent = async () => {
      // Initialize uploaded files
      try {
        await fetchUploadedFiles()
      } catch (error) {
        console.error('Error fetching uploaded files:', error)
      }

      // Initialize chat
      try {
        const chats = await chatAPI.listChats()
        if (chats.length > 0) {
          handleChatSelect(chats[0].id)
        } else {
          const newChat = await chatAPI.createChat()
          setCurrentChatId(newChat.id)
        }
      } catch (error) {
        console.error('Error initializing chat:', error)
        // Fallback: work without chat management if backend is not available
        setCurrentChatId('local-chat')
        setError('Chat management unavailable - working in local mode')
      }
    }
    
    initializeComponent()
  }, [])

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && showResetConfirm) {
        setShowResetConfirm(false)
      }
    }
    
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [showResetConfirm])

  // Chat Management Functions
  const handleChatSelect = async (chatId) => {
    try {
      setCurrentChatId(chatId)
      const chatData = await chatAPI.getChat(chatId)
      
      // Convert chat messages to display format
      const formattedMessages = [
        {
          id: 0,
          type: 'bot',
          content: 'Hello! I\'m your AI assistant. You can ask me questions or upload PDF documents for me to analyze.',
          timestamp: new Date()
        },
        ...chatData.messages.map((msg, index) => ({
          id: index + 1,
          type: msg.type, // Use msg.type directly from backend
          content: msg.content,
          timestamp: new Date(msg.timestamp),
          ...(msg.metadata && { 
            metadata: {
              selectedDocument: msg.metadata.selected_document
            }
          })
        }))
      ]
      
      setMessages(formattedMessages)
    } catch (error) {
      console.error('Error loading chat:', error)
      setError('Failed to load chat history')
    }
  }

  const handleToggleSidebar = () => {
    setSidebarOpen(!sidebarOpen)
  }

  const fetchUploadedFiles = async () => {
    try {
      const data = await chatAPI.getUploadedFiles()
      setUploadedFiles(data.documents || [])
    } catch (error) {
      console.error('Error fetching uploaded files:', error)
    }
  }

  const handleResetChat = () => {
    if (messages.length <= 1) {
      // Already at initial state, no need to reset
      return
    }
    
    setShowResetConfirm(true)
  }

  const confirmResetChat = () => {
    const initialMessage = {
      id: 1,
      type: 'bot',
      content: 'Hello! I\'m your AI assistant. You can ask me questions or upload PDF documents for me to analyze.',
      timestamp: new Date()
    }
    setMessages([initialMessage])
    setInputMessage('')
    setError(null)
    setShowUpload(false)
    setShowResetConfirm(false)
  }

  const cancelResetChat = () => {
    setShowResetConfirm(false)
  }

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)
    setError(null)
    setDebugInfo(null) // Reset debug info

    try {
      console.log('📤 Sending message:', inputMessage)
      console.log('💬 Using chat ID:', currentChatId)
      // Use streaming API
      await chatAPI.sendMessageStream(
        inputMessage,
        currentChatId === 'local-chat' ? null : currentChatId, // Don't send chat_id for local mode
        // On final answer
        (data) => {
          console.log('✅ Final answer received:', data)
          console.log('✅ Answer length:', data.answer?.length || 0)
          const botMessage = {
            id: Date.now() + 1,
            type: 'bot',
            content: preprocessAIResponse(data.answer),
            timestamp: new Date(),
            metadata: {
              selectedDocument: data.selected_document,
              selectionScore: data.selection_score,
              documentsConsidered: data.documents_considered
            }
          }
          setMessages(prev => [...prev, botMessage])
        },
        // On error
        (error) => {
          console.error('Error sending message:', error)
          const errorMessage = {
            id: Date.now() + 1,
            type: 'bot',
            content: 'Sorry, I encountered an error while processing your request. Please try again.',
            timestamp: new Date(),
            isError: true
          }
          setMessages(prev => [...prev, errorMessage])
          setError(error.message || 'Network error occurred')
        },
        // On debug
        (data) => {
          console.log('🔍 Debug callback received:', data)
          setDebugInfo(data)
        }
      )
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: 'Sorry, I encountered an error while processing your request. Please try again.',
        timestamp: new Date(),
        isError: true
      }
      setMessages(prev => [...prev, errorMessage])
      setError(error.message || 'Network error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileUpload = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please upload only PDF files')
      return
    }

    if (file.size > 50 * 1024 * 1024) {
      setError('File size must be less than 50MB')
      return
    }

    setIsUploading(true)
    setError(null)

    try {
      const data = await chatAPI.uploadFile(file)

      const uploadMessage = {
        id: Date.now(),
        type: 'system',
        content: `Successfully uploaded: ${data.filename}`,
        timestamp: new Date(),
        isSuccess: true
      }

      setMessages(prev => [...prev, uploadMessage])
      await fetchUploadedFiles()
      setShowUpload(false)
    } catch (error) {
      console.error('Error uploading file:', error)
      setError(error.message || 'Failed to upload file')
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  }

  const handleTestMarkdown = () => {
    const testMessage = {
      id: Date.now(),
      type: 'bot',
      content: `# Markdown Test

Here's a demonstration of various markdown features:

## Code Blocks
\`\`\`python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))  # Output: 55
\`\`\`

## Inline Code
Use \`npm install\` to install dependencies.

## Lists
- **Bullet point 1**
- *Bullet point 2*
- Regular bullet point

1. First numbered item
2. Second numbered item
3. Third numbered item

## Tables
| Feature | Status | Notes |
|---------|--------|-------|
| Markdown | ✅ Working | Full support |
| Code highlighting | ✅ Working | Syntax aware |
| Math equations | ✅ Working | LaTeX support |

## Math (LaTeX)
Inline math: $E = mc^2$

Block math:
$$\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}$$

## Blockquote
> This is a blockquote example
> It can span multiple lines

## Links
Check out [React](https://react.dev) for more information.

**Bold text** and *italic text* work perfectly!`,
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, testMessage])
  }

  return (
    <div className="chatbot-container">
      <ChatSidebar 
        currentChatId={currentChatId}
        onChatSelect={handleChatSelect}
        isOpen={sidebarOpen}
        onToggle={handleToggleSidebar}
      />
      <div className={`chatbot-main ${sidebarOpen ? 'with-sidebar' : ''}`}>
        <div className="chatbot-header">
          <div className="header-left">
            <Bot className="bot-icon" />
            <div>
              <h1>AI Document Assistant</h1>
              <p className="status">
                {uploadedFiles.length > 0 ? (
                  `${uploadedFiles.length} document(s) available`
                ) : (
                  'No documents uploaded'
                )}
              </p>
            </div>
          </div>
        <div className="header-actions">
          <button 
            className="reset-button"
            onClick={handleResetChat}
            title="Reset Chat"
            disabled={messages.length <= 1}
          >
            <RotateCcw size={20} />
          </button>
          <button 
            className={`upload-toggle ${showUpload ? 'active' : ''}`}
            onClick={() => setShowUpload(!showUpload)}
            title="Upload PDF"
          >
            <Upload size={20} />
          </button>
        </div>
      </div>

      {showUpload && (
        <div className="upload-section">
          <div className="upload-area">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
            />
            <button 
              className="upload-button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
            >
              {isUploading ? (
                <>
                  <Loader2 className="spin" size={20} />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload size={20} />
                  Choose PDF File
                </>
              )}
            </button>
            <p className="upload-hint">Max file size: 50MB</p>
          </div>
          
          {uploadedFiles.length > 0 && (
            <div className="uploaded-files">
              <h3>Uploaded Documents:</h3>
              <div className="files-list">
                {uploadedFiles.map((file, index) => (
                  <div key={index} className="file-item">
                    <FileText size={16} />
                    <span>{file.name}</span>
                    <span className="file-status">{file.status}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="error-banner">
          <AlertCircle size={16} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {showResetConfirm && (
        <div className="reset-confirmation-modal" onClick={cancelResetChat}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Confirm Reset</h2>
            <p>Are you sure you want to reset the chat? This will clear all messages and cannot be undone.</p>
            <div className="modal-actions">
              <button onClick={confirmResetChat} className="confirm-button">
                <CheckCircle size={16} />
                Yes, reset
              </button>
              <button onClick={cancelResetChat} className="cancel-button">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Debug info display (development only) */}
      {debugInfo && process.env.NODE_ENV === 'development' && (
        <div className="debug-info-banner" style={{
          backgroundColor: '#f0f8ff',
          border: '1px solid #87ceeb',
          padding: '8px 12px',
          margin: '8px',
          borderRadius: '4px',
          fontSize: '12px',
          fontFamily: 'monospace',
          color: '#2c3e50'
        }}>
          🔍 Debug: {debugInfo.message} | Intent: {debugInfo.intent}
        </div>
      )}

      <div className="messages-container">
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.type}`}>
            <div className="message-avatar">
              {message.type === 'user' ? <User size={20} /> : <Bot size={20} />}
            </div>
            <div className="message-content">
              <div className={`message-bubble ${message.isError ? 'error' : ''} ${message.isSuccess ? 'success' : ''}`}>
                <MessageContent content={message.content} type={message.type} />
                {message.metadata && message.metadata.selectedDocument && (
                  <div className="message-metadata">
                    <div className="metadata-item source-document">
                      <FileText size={14} />
                      <span className="source-label">Answer generated from:</span>
                      <span className="source-name">{message.metadata.selectedDocument}</span>
                    </div>
                  </div>
                )}
              </div>
              <span className="message-time">{formatTimestamp(message.timestamp)}</span>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="message bot">
            <div className="message-avatar">
              <Bot size={20} />
            </div>
            <div className="message-content">
              <div className="message-bubble typing">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="input-container">
        <div className="input-wrapper">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me anything about your documents..."
            className="message-input"
            rows="1"
            disabled={isLoading}
          />
          <button 
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || isLoading}
            className="send-button"
          >
            {isLoading ? (
              <Loader2 className="spin" size={20} />
            ) : (
              <Send size={20} />
            )}
          </button>
        </div>
      </div>
      </div>
    </div>
  )
}

export default Chatbot
