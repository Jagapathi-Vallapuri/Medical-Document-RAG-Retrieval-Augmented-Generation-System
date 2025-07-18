import React, { useState, useEffect } from 'react'
import { chatAPI } from '../services/api'
import './ChatSidebar.css'

const ChatSidebar = ({ currentChatId, onChatSelect, isOpen, onToggle }) => {
  const [chats, setChats] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [editingChatId, setEditingChatId] = useState(null)
  const [editTitle, setEditTitle] = useState('')

  useEffect(() => {
    loadChats()
  }, [])

  const loadChats = async () => {
    try {
      setLoading(true)
      const chatList = await chatAPI.listChats()
      // Ensure chatList is an array
      setChats(Array.isArray(chatList) ? chatList : [])
    } catch (err) {
      setError('Failed to load chats')
      console.error('Error loading chats:', err)
      setChats([]) // Set empty array on error
    } finally {
      setLoading(false)
    }
  }

  const handleCreateChat = async () => {
    try {
      const newChat = await chatAPI.createChat()
      if (newChat && newChat.id) {
        // Format the new chat to match the list format
        const formattedChat = {
          id: newChat.id,
          chat_id: newChat.id,
          title: newChat.title || 'New Chat',
          message_count: 0,
          created_at: newChat.created_at || new Date().toISOString(),
          updated_at: newChat.updated_at || new Date().toISOString(),
          last_message: ''
        }
        setChats(prevChats => [formattedChat, ...prevChats])
        onChatSelect(newChat.id)
      }
    } catch (err) {
      setError('Failed to create chat')
      console.error('Error creating chat:', err)
    }
  }

  const handleDeleteChat = async (chatId, e) => {
    e.stopPropagation()
    try {
      await chatAPI.deleteChat(chatId)
      setChats(prevChats => prevChats.filter(chat => chat.id !== chatId))
      
      // If deleting current chat, select the first available chat or create new one
      if (chatId === currentChatId) {
        const remainingChats = chats.filter(chat => chat.id !== chatId)
        if (remainingChats.length > 0) {
          onChatSelect(remainingChats[0].id)
        } else {
          handleCreateChat()
        }
      }
    } catch (err) {
      setError('Failed to delete chat')
      console.error('Error deleting chat:', err)
    }
  }

  const handleEditChat = (chatId, currentTitle, e) => {
    e.stopPropagation()
    setEditingChatId(chatId)
    setEditTitle(currentTitle)
  }

  const handleSaveEdit = async (chatId, e) => {
    if (e) e.stopPropagation()
    
    const trimmedTitle = editTitle.trim()
    if (!trimmedTitle) {
      setError('Chat title cannot be empty')
      return
    }

    // Don't save if title hasn't changed
    const currentChat = chats.find(chat => (chat.id || chat.chat_id) === chatId)
    if (currentChat && currentChat.title === trimmedTitle) {
      setEditingChatId(null)
      setEditTitle('')
      return
    }

    try {
      await chatAPI.updateChat(chatId, trimmedTitle)
      
      // Update the chat in the local state
      setChats(prevChats => 
        prevChats.map(chat => 
          (chat.id || chat.chat_id) === chatId 
            ? { ...chat, title: trimmedTitle, updated_at: new Date().toISOString() }
            : chat
        )
      )
      
      setEditingChatId(null)
      setEditTitle('')
      setError(null) // Clear any previous errors
    } catch (err) {
      setError('Failed to update chat title')
      console.error('Error updating chat:', err)
    }
  }

  const handleCancelEdit = (e) => {
    if (e) e.stopPropagation()
    setEditingChatId(null)
    setEditTitle('')
  }

  const handleKeyPress = (e, chatId) => {
    if (e.key === 'Enter') {
      handleSaveEdit(chatId, e)
    } else if (e.key === 'Escape') {
      handleCancelEdit(e)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Just now'
    
    const date = new Date(dateString)
    if (isNaN(date.getTime())) return 'Just now' // Handle invalid dates
    
    const now = new Date()
    const diffInHours = (now - date) / (1000 * 60 * 60)
    
    if (diffInHours < 24) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } else if (diffInHours < 168) { // 7 days
      return date.toLocaleDateString([], { weekday: 'short' })
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    }
  }

  return (
    <div className={`chat-sidebar ${isOpen ? 'open' : 'closed'}`}>
      <div className="sidebar-header">
        <button className="toggle-btn" onClick={onToggle}>
          {isOpen ? '◀' : '▶'}
        </button>
        {isOpen && (
          <>
            <h3>Chats</h3>
            <button className="new-chat-btn" onClick={handleCreateChat}>
              + New Chat
            </button>
          </>
        )}
      </div>

      {isOpen && (
        <div className="sidebar-content">
          {error && <div className="error-message">{error}</div>}
          
          {loading ? (
            <div className="loading">Loading chats...</div>
          ) : (
            <div className="chat-list">
              {Array.isArray(chats) && chats.map(chat => {
                const chatId = chat.id || chat.chat_id
                const isEditing = editingChatId === chatId
                
                return (
                  <div
                    key={chatId}
                    className={`chat-item ${chatId === currentChatId ? 'active' : ''}`}
                    onClick={() => !isEditing && onChatSelect(chatId)}
                  >
                    <div className="chat-content">
                      {isEditing ? (
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          onKeyDown={(e) => handleKeyPress(e, chatId)}
                          onBlur={() => handleSaveEdit(chatId)}
                          className="chat-title-input"
                          autoFocus
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <div className="chat-title">{chat.title || 'Untitled Chat'}</div>
                      )}
                    </div>
                    <div className="chat-meta">
                      <span className="chat-date">{formatDate(chat.updated_at)}</span>
                      <div className="chat-actions">
                        {isEditing ? (
                          <>
                            <button
                              className="save-btn"
                              onClick={(e) => handleSaveEdit(chatId, e)}
                              title="Save"
                            >
                              ✓
                            </button>
                            <button
                              className="cancel-btn"
                              onClick={handleCancelEdit}
                              title="Cancel"
                            >
                              ✕
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              className="edit-btn"
                              onClick={(e) => handleEditChat(chatId, chat.title, e)}
                              title="Rename chat"
                            >
                              ✏️
                            </button>
                            <button
                              className="delete-btn"
                              onClick={(e) => handleDeleteChat(chatId, e)}
                              title="Delete chat"
                            >
                              ✕
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
              
              {chats.length === 0 && (
                <div className="empty-state">
                  No chats yet. Create your first chat!
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ChatSidebar
