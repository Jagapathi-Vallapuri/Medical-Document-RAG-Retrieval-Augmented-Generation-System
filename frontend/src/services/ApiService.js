export class ApiService {
  constructor() {
    this.baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  }

  async sendMessage(message, selectedDocuments = []) {
    try {
      const response = await fetch(`${this.baseURL}/ask/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          documents: selectedDocuments,
          document_ids: selectedDocuments 
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Error sending message:', error)
      throw error
    }
  }

  async uploadFile(file) {
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${this.baseURL}/upload_pdf/`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Error uploading file:', error)
      throw error
    }
  }

  async getDocuments() {
    try {
      const response = await fetch(`${this.baseURL}/list_pdfs/`)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Error fetching documents:', error)
      throw error
    }
  }
}