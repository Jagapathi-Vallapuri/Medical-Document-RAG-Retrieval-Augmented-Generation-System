import './style.css'
import { ChatInterface } from './components/ChatInterface.js'
import { FileUpload } from './components/FileUpload.js'
import { DocumentSelector } from './components/DocumentSelector.js'
import { ApiService } from './services/ApiService.js'

class App {
  constructor() {
    this.apiService = new ApiService()
    this.documentSelector = new DocumentSelector(this.apiService)
    this.chatInterface = new ChatInterface(this.apiService, this.documentSelector)
    this.fileUpload = new FileUpload(this.apiService)
    this.init()
  }

  init() {
    const app = document.querySelector('#app')
    app.innerHTML = `
      <div class="app-container">
        <header class="app-header">
          <div class="header-content">
            <div class="logo">
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                <rect width="32" height="32" rx="8" fill="url(#gradient)"/>
                <path d="M16 8L24 16L16 24L8 16L16 8Z" fill="white" opacity="0.9"/>
                <defs>
                  <linearGradient id="gradient" x1="0" y1="0" x2="32" y2="32">
                    <stop stop-color="#667eea"/>
                    <stop offset="1" stop-color="#764ba2"/>
                  </linearGradient>
                </defs>
              </svg>
              <h1>AI Assistant</h1>
            </div>
            <div class="header-actions">
              <button class="upload-btn" id="uploadBtn">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="7,10 12,15 17,10"/>
                  <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                Upload Files
              </button>
            </div>
          </div>
        </header>
        
        <main class="app-main">
          <div class="main-content">
            <aside class="sidebar">
              <div class="sidebar-header">
                <h3>Documents</h3>
                <button class="refresh-docs-btn" id="refreshDocsBtn" title="Refresh documents">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="23 4 23 10 17 10"/>
                    <polyline points="1 20 1 14 7 14"/>
                    <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
                  </svg>
                </button>
              </div>
              <div class="sidebar-content" id="documentSelector">
                <!-- Document selector will be inserted here -->
              </div>
            </aside>
            
            <div class="chat-container" id="chatContainer">
              <!-- Chat interface will be inserted here -->
            </div>
          </div>
          
          <div class="upload-overlay" id="uploadOverlay">
            <div class="upload-modal">
              <div class="upload-header">
                <h3>Upload Documents</h3>
                <button class="close-btn" id="closeUpload">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>
              <div class="upload-content" id="uploadContent">
                <!-- File upload interface will be inserted here -->
              </div>
            </div>
          </div>
        </main>
      </div>
    `

    // Initialize components
    this.documentSelector.mount(document.getElementById('documentSelector'))
    this.chatInterface.mount(document.getElementById('chatContainer'))
    this.fileUpload.mount(document.getElementById('uploadContent'))

    // Set up document selector callback
    this.documentSelector.onSelectionChange = (selectedDocs) => {
      // You can add additional logic here when selection changes
      console.log('Selected documents:', selectedDocs)
    }

    // Setup event listeners
    this.setupEventListeners()
  }

  setupEventListeners() {
    const uploadBtn = document.getElementById('uploadBtn')
    const uploadOverlay = document.getElementById('uploadOverlay')
    const closeUpload = document.getElementById('closeUpload')
    const refreshDocsBtn = document.getElementById('refreshDocsBtn')

    uploadBtn.addEventListener('click', () => {
      uploadOverlay.classList.add('active')
    })

    closeUpload.addEventListener('click', () => {
      uploadOverlay.classList.remove('active')
    })

    uploadOverlay.addEventListener('click', (e) => {
      if (e.target === uploadOverlay) {
        uploadOverlay.classList.remove('active')
      }
    })

    refreshDocsBtn.addEventListener('click', () => {
      this.documentSelector.refreshDocuments()
    })

    // Refresh documents when files are successfully uploaded
    this.fileUpload.onUploadSuccess = () => {
      this.documentSelector.refreshDocuments()
    }
  }
}

// Initialize the app
new App()