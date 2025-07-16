export class DocumentSelector {
  constructor(apiService) {
    this.apiService = apiService
    this.documents = []
    this.selectedDocument = null // Changed from Set to single selection
    this.onSelectionChange = null
  }

  mount(container) {
    this.container = container
    this.loadDocuments()
  }

  async loadDocuments() {
    try {
      const response = await this.apiService.getDocuments()
      // Handle both 'documents' and 'pdfs' response formats
      this.documents = response.documents || response.pdfs || []
      // Convert simple filenames to document objects if needed
      if (this.documents.length > 0 && typeof this.documents[0] === 'string') {
        this.documents = this.documents.map((filename, index) => ({
          id: filename,
          name: filename,
          type: 'pdf',
          status: 'Ready'
        }))
      }
      this.render()
      // Only setup event listeners if we have documents
      if (this.documents.length > 0) {
        this.setupEventListeners()
      }
    } catch (error) {
      console.error('Error loading documents:', error)
      this.renderError()
    }
  }

  render() {
    if (this.documents.length === 0) {
      this.container.innerHTML = `
        <div class="document-selector empty">
          <div class="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14,2 14,8 20,8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10,9 9,9 8,9"/>
            </svg>
            <h4>No Documents Available</h4>
            <p>Upload some documents first to start asking questions</p>
          </div>
        </div>
      `
      return
    }

    this.container.innerHTML = `
      <div class="document-selector">
        <div class="selector-header">
          <h4>Select Document to Query</h4>
        </div>
        
        <div class="document-list" id="documentList">
          ${this.documents.map(doc => `
            <div class="document-item ${this.selectedDocument === doc.id ? 'selected' : ''}" 
                 data-id="${doc.id}">
              <div class="document-checkbox">
                <input type="radio" 
                       name="document-selection"
                       id="doc-${doc.id}" 
                       ${this.selectedDocument === doc.id ? 'checked' : ''}
                       data-doc-id="${doc.id}">
                <label for="doc-${doc.id}"></label>
              </div>
              <div class="document-info">
                <div class="document-icon">
                  ${this.getDocumentIcon(doc.type || doc.name)}
                </div>
                <div class="document-details">
                  <div class="document-name">${doc.name}</div>
                </div>
              </div>
              <div class="document-status">
                <span class="status-badge ${doc.status || 'processed'}">${doc.status || 'Ready'}</span>
              </div>
            </div>
          `).join('')}
        </div>
        
        <div class="selection-summary">
          <span class="selected-count">${this.selectedDocument ? '1 document selected' : 'No document selected'}</span>
        </div>
      </div>
    `
  }

  renderError() {
    this.container.innerHTML = `
      <div class="document-selector error">
        <div class="error-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          <h4>Error Loading Documents</h4>
          <p>Unable to load your documents. Please try again.</p>
          <button class="retry-btn" onclick="this.loadDocuments()">Retry</button>
        </div>
      </div>
    `
  }

  setupEventListeners() {
    const documentList = document.getElementById('documentList')

    // Check if elements exist before adding event listeners
    if (!documentList) {
      return // No documents to set up listeners for
    }

    // Handle individual document selection
    documentList.addEventListener('change', (e) => {
      if (e.target.type === 'radio') {
        const docId = e.target.dataset.docId
        this.selectedDocument = docId
        this.updateSelection()
      }
    })

    // Handle document item clicks (toggle selection)
    documentList.addEventListener('click', (e) => {
      const documentItem = e.target.closest('.document-item')
      if (documentItem && !e.target.closest('.document-checkbox')) {
        const radioButton = documentItem.querySelector('input[type="radio"]')
        radioButton.click()
      }
    })
  }

  updateSelection() {
    // Update UI
    const selectedCount = document.querySelector('.selected-count')
    if (selectedCount) {
      selectedCount.textContent = this.selectedDocument ? '1 document selected' : 'No document selected'
    }

    // Update document items
    document.querySelectorAll('.document-item').forEach(item => {
      const docId = item.dataset.id
      if (this.selectedDocument === docId) {
        item.classList.add('selected')
      } else {
        item.classList.remove('selected')
      }
    })

    // Notify parent component
    if (this.onSelectionChange) {
      this.onSelectionChange(this.selectedDocument ? [this.selectedDocument] : [])
    }
  }

  getSelectedDocuments() {
    return this.selectedDocument ? [this.selectedDocument] : []
  }

  getDocumentIcon(nameOrType) {
    const name = nameOrType.toLowerCase()
    if (name.includes('.pdf') || nameOrType === 'pdf') {
      return '<svg width="20" height="20" viewBox="0 0 24 24" fill="#dc2626"><path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/></svg>'
    } else if (name.includes('.txt') || nameOrType === 'txt') {
      return '<svg width="20" height="20" viewBox="0 0 24 24" fill="#6b7280"><path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/></svg>'
    } else if (name.includes('.doc') || nameOrType === 'doc') {
      return '<svg width="20" height="20" viewBox="0 0 24 24" fill="#2563eb"><path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/></svg>'
    } else {
      return '<svg width="20" height="20" viewBox="0 0 24 24" fill="#059669"><path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/></svg>'
    }
  }

  refreshDocuments() {
    this.loadDocuments()
  }
}