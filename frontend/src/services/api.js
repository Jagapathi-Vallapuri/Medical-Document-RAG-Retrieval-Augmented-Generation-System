import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes timeout
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // You can add auth tokens here if needed
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // Handle common errors
    if (error.code === 'ECONNABORTED') {
      error.message = 'Request timeout. Please try again.'
    } else if (error.response?.status === 500) {
      error.message = 'Server error. Please try again later.'
    } else if (error.response?.status === 404) {
      error.message = 'Service not found. Make sure the backend is running.'
    } else if (!error.response) {
      error.message = 'Network error. Please check your connection and ensure the backend is running.'
    }
    return Promise.reject(error)
  }
)

export const chatAPI = {
  // Send a message to the chatbot
  sendMessage: async (message, chatId = null) => {
    const response = await api.post('/auto_ask/', { message, chat_id: chatId })
    return response.data
  },

  // Send a message with streaming
  sendMessageStream: async (message, chatId, onFinalAnswer, onError, onDebug = null) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auto_ask_stream/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message, chat_id: chatId }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              if (data.type === 'final_answer') {
                console.log('🔄 API: Final answer event:', data)
                onFinalAnswer(data)
              } else if (data.type === 'error') {
                console.error('🔄 API: Error event:', data)
                onError(new Error(data.error))
              } else if (data.type === 'debug') {
                console.log('🔍 API: Debug info:', data)
                if (onDebug) onDebug(data)
              } else if (data.type === 'direct_answer') {
                console.log('🔄 API: Direct answer processing:', data)
              } else {
                console.log('🔄 API: Unknown event type:', data.type, data)
              }
            } catch (e) {
              console.warn('Failed to parse SSE data:', line)
            }
          }
        }
      }
    } catch (error) {
      onError(error)
    }
  },

  // Chat Management APIs
  createChat: async (title = 'New Chat') => {
    const response = await api.post('/chats/', { title })
    return { id: response.data.chat_id, ...response.data } // Normalize id field
  },

  listChats: async () => {
    const response = await api.get('/chats/')
    const chats = response.data.chats || []
    // Normalize id field for consistency
    return chats.map(chat => ({ 
      id: chat.chat_id || chat.id, 
      ...chat 
    }))
  },

  getChat: async (chatId) => {
    const response = await api.get(`/chats/${chatId}`)
    return response.data
  },

  updateChat: async (chatId, title) => {
    const response = await api.put(`/chats/${chatId}`, { title })
    return response.data
  },

  deleteChat: async (chatId) => {
    const response = await api.delete(`/chats/${chatId}`)
    return response.data
  },

  // Upload a PDF file
  uploadFile: async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await api.post('/upload_pdf/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  // Get list of uploaded PDFs
  getUploadedFiles: async () => {
    const response = await api.get('/list_pdfs/')
    return response.data
  },

  // Health check
  healthCheck: async () => {
    const response = await api.get('/health/')
    return response.data
  },

  // Chat Logs APIs
  getChatLogs: async (chatId) => {
    const response = await api.get(`/chats/${chatId}/logs`)
    return response.data
  },

  getAllChatLogsSummary: async () => {
    const response = await api.get('/chats/logs/summary')
    return response.data
  },

  cleanupOldLogs: async (daysToKeep = 30) => {
    const response = await api.post('/admin/cleanup-logs', { days_to_keep: daysToKeep })
    return response.data
  },
}

export default api
