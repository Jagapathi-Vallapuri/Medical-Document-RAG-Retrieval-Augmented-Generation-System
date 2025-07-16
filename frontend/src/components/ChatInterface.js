import { markdownToHtml } from '../utils/markdown.js'

export class ChatInterface {
  constructor(apiService, documentSelector) {
    this.apiService = apiService
    this.documentSelector = documentSelector
    this.messages = []
    this.isTyping = false
  }

  mount(container) {
    this.container = container
    this.render()
    this.setupEventListeners()
    this.addWelcomeMessage()
  }

  render() {
    this.container.innerHTML = `
      <div class="chat-messages" id="chatMessages">
        <!-- Messages will be inserted here -->
      </div>
      
      <div class="chat-input-container">
        <div class="chat-input-wrapper">
          <textarea 
            class="chat-input" 
            id="chatInput" 
            placeholder="Ask me anything..."
            rows="1"
          ></textarea>
          <button class="send-btn" id="sendBtn" disabled>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22,2 15,22 11,13 2,9 22,2"/>
            </svg>
          </button>
        </div>
        <div class="input-hint">
          Press Enter to send, Shift+Enter for new line
        </div>
      </div>
    `
  }

  setupEventListeners() {
    const chatInput = document.getElementById('chatInput')
    const sendBtn = document.getElementById('sendBtn')

    chatInput.addEventListener('input', () => {
      this.autoResize(chatInput)
      sendBtn.disabled = !chatInput.value.trim()
    })

    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        this.sendMessage()
      }
    })

    sendBtn.addEventListener('click', () => {
      this.sendMessage()
    })
  }

  autoResize(textarea) {
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px'
  }

  addWelcomeMessage() {
    const welcomeMessage = {
      type: 'assistant',
      content: 'Hello! I\'m your AI assistant. Please select the documents you\'d like to query from the sidebar, then ask me any questions about them. How can I assist you today?',
      timestamp: new Date()
    }
    this.addMessage(welcomeMessage)
  }

  async sendMessage() {
    const chatInput = document.getElementById('chatInput')
    const message = chatInput.value.trim()
    
    if (!message || this.isTyping) return

    // Check if documents are selected
    const selectedDocs = this.documentSelector.getSelectedDocuments()
    if (selectedDocs.length === 0) {
      this.addMessage({
        type: 'assistant',
        content: 'Please select at least one document from the sidebar before asking questions.',
        timestamp: new Date()
      })
      return
    }
    // Add user message
    this.addMessage({
      type: 'user',
      content: message,
      timestamp: new Date()
    })

    // Clear input
    chatInput.value = ''
    chatInput.style.height = 'auto'
    document.getElementById('sendBtn').disabled = true

    // Show typing indicator
    this.showTypingIndicator()

    try {
      // Send message to backend
      const response = await this.apiService.sendMessage(message, selectedDocs)
      
      // Remove typing indicator
      this.hideTypingIndicator()
      
      // Add assistant response
      this.addMessage({
        type: 'assistant',
        content: response.message || response.response || 'I apologize, but I encountered an issue processing your request.',
        timestamp: new Date()
      })
    } catch (error) {
      console.error('Error sending message:', error)
      this.hideTypingIndicator()
      
      this.addMessage({
        type: 'assistant',
        content: 'I apologize, but I\'m having trouble connecting to the server. Please try again later.',
        timestamp: new Date()
      })
    }
  }

  addMessage(message) {
    this.messages.push(message)
    this.renderMessages()
    this.scrollToBottom()
  }

  renderMessages() {
    const messagesContainer = document.getElementById('chatMessages')
    messagesContainer.innerHTML = this.messages.map(message => `
      <div class="message ${message.type}">
        <div class="message-avatar">
          ${message.type === 'user' ? 
            '<div class="user-avatar">You</div>' : 
            '<div class="assistant-avatar">AI</div>'
          }
        </div>
        <div class="message-content">
          <div class="message-text">${this.formatMessage(message.content)}</div>
          <div class="message-time">${this.formatTime(message.timestamp)}</div>
        </div>
      </div>
    `).join('')
  }

  formatMessage(content) {
    // Use proper markdown parser for rich formatting
    return markdownToHtml(content)
  }

  formatTime(timestamp) {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  showTypingIndicator() {
    this.isTyping = true
    const messagesContainer = document.getElementById('chatMessages')
    const typingIndicator = document.createElement('div')
    typingIndicator.className = 'message assistant typing-indicator'
    typingIndicator.id = 'typingIndicator'
    typingIndicator.innerHTML = `
      <div class="message-avatar">
        <div class="assistant-avatar">AI</div>
      </div>
      <div class="message-content">
        <div class="typing-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    `
    messagesContainer.appendChild(typingIndicator)
    this.scrollToBottom()
  }

  hideTypingIndicator() {
    this.isTyping = false
    const typingIndicator = document.getElementById('typingIndicator')
    if (typingIndicator) {
      typingIndicator.remove()
    }
  }

  scrollToBottom() {
    const messagesContainer = document.getElementById('chatMessages')
    messagesContainer.scrollTop = messagesContainer.scrollHeight
  }
}