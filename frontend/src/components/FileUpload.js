export class FileUpload {
  constructor(apiService) {
    this.apiService = apiService
    this.uploadedFiles = []
    this.onUploadSuccess = null
  }

  mount(container) {
    this.container = container
    this.render()
    this.setupEventListeners()
  }

  render() {
    this.container.innerHTML = `
      <div class="upload-area" id="uploadArea">
        <div class="upload-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-15"/>
            <polyline points="7,10 12,15 17,10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
        </div>
        <div class="upload-text">
          <h4>Drop files here or click to browse</h4>
          <p>Supports PDF, TXT, DOC, DOCX files up to 10MB</p>
        </div>
        <input type="file" id="fileInput" multiple accept=".pdf,.txt,.doc,.docx" hidden>
      </div>
      
      <div class="uploaded-files" id="uploadedFiles">
        <!-- Uploaded files will be shown here -->
      </div>
      
      <div class="upload-actions">
        <button class="btn-secondary" id="clearFiles">Clear All</button>
        <button class="btn-primary" id="processFiles" disabled>Process Files</button>
      </div>
    `
  }

  setupEventListeners() {
    const uploadArea = document.getElementById('uploadArea')
    const fileInput = document.getElementById('fileInput')
    const clearFiles = document.getElementById('clearFiles')
    const processFiles = document.getElementById('processFiles')

    // Click to browse
    uploadArea.addEventListener('click', () => {
      fileInput.click()
    })

    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
      e.preventDefault()
      uploadArea.classList.add('drag-over')
    })

    uploadArea.addEventListener('dragleave', () => {
      uploadArea.classList.remove('drag-over')
    })

    uploadArea.addEventListener('drop', (e) => {
      e.preventDefault()
      uploadArea.classList.remove('drag-over')
      this.handleFiles(e.dataTransfer.files)
    })

    // File input change
    fileInput.addEventListener('change', (e) => {
      this.handleFiles(e.target.files)
    })

    // Clear files
    clearFiles.addEventListener('click', () => {
      this.clearAllFiles()
    })

    // Process files
    processFiles.addEventListener('click', () => {
      this.processAllFiles()
    })
  }

  handleFiles(files) {
    Array.from(files).forEach(file => {
      if (this.validateFile(file)) {
        this.addFile(file)
      }
    })
    this.updateUI()
  }

  validateFile(file) {
    const maxSize = 10 * 1024 * 1024 // 10MB
    const allowedTypes = ['application/pdf', 'text/plain', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    
    if (file.size > maxSize) {
      this.showError(`File "${file.name}" is too large. Maximum size is 10MB.`)
      return false
    }
    
    if (!allowedTypes.includes(file.type)) {
      this.showError(`File "${file.name}" is not supported. Please upload PDF, TXT, DOC, or DOCX files.`)
      return false
    }
    
    return true
  }

  addFile(file) {
    const fileObj = {
      id: Date.now() + Math.random(),
      file: file,
      name: file.name,
      size: file.size,
      status: 'pending'
    }
    
    this.uploadedFiles.push(fileObj)
  }

  updateUI() {
    this.renderUploadedFiles()
    const processBtn = document.getElementById('processFiles')
    processBtn.disabled = this.uploadedFiles.length === 0
  }

  renderUploadedFiles() {
    const container = document.getElementById('uploadedFiles')
    
    if (this.uploadedFiles.length === 0) {
      container.innerHTML = ''
      return
    }
    
    container.innerHTML = `
      <h4>Selected Files (${this.uploadedFiles.length})</h4>
      <div class="file-list">
        ${this.uploadedFiles.map(fileObj => `
          <div class="file-item ${fileObj.status}" data-id="${fileObj.id}">
            <div class="file-info">
              <div class="file-icon">
                ${this.getFileIcon(fileObj.file.type)}
              </div>
              <div class="file-details">
                <div class="file-name">${fileObj.name}</div>
                <div class="file-size">${this.formatFileSize(fileObj.size)}</div>
              </div>
            </div>
            <div class="file-status">
              ${this.getStatusIcon(fileObj.status)}
            </div>
            <button class="remove-file" onclick="window.fileUpload.removeFile('${fileObj.id}')">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        `).join('')}
      </div>
    `
  }

  getFileIcon(type) {
    if (type === 'application/pdf') {
      return '<svg width="20" height="20" viewBox="0 0 24 24" fill="#dc2626"><path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/></svg>'
    } else if (type === 'text/plain') {
      return '<svg width="20" height="20" viewBox="0 0 24 24" fill="#6b7280"><path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/></svg>'
    } else {
      return '<svg width="20" height="20" viewBox="0 0 24 24" fill="#2563eb"><path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/></svg>'
    }
  }

  getStatusIcon(status) {
    switch (status) {
      case 'pending':
        return '<svg width="16" height="16" viewBox="0 0 24 24" fill="#6b7280"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>'
      case 'uploading':
        return '<div class="spinner"></div>'
      case 'success':
        return '<svg width="16" height="16" viewBox="0 0 24 24" fill="#10b981"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22,4 12,14.01 9,11.01"/></svg>'
      case 'error':
        return '<svg width="16" height="16" viewBox="0 0 24 24" fill="#ef4444"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
      default:
        return ''
    }
  }

  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  removeFile(id) {
    this.uploadedFiles = this.uploadedFiles.filter(file => file.id !== id)
    this.updateUI()
  }

  clearAllFiles() {
    this.uploadedFiles = []
    this.updateUI()
  }

  async processAllFiles() {
    if (this.uploadedFiles.length === 0) return

    const processBtn = document.getElementById('processFiles')
    processBtn.disabled = true
    processBtn.textContent = 'Processing...'

    for (const fileObj of this.uploadedFiles) {
      fileObj.status = 'uploading'
      this.updateUI()

      try {
        await this.apiService.uploadFile(fileObj.file)
        fileObj.status = 'success'
      } catch (error) {
        console.error('Upload error:', error)
        fileObj.status = 'error'
      }
      
      this.updateUI()
    }

    processBtn.disabled = false
    processBtn.textContent = 'Process Files'
    
    const successCount = this.uploadedFiles.filter(f => f.status === 'success').length
    if (successCount > 0) {
      this.showSuccess(`Successfully processed ${successCount} file(s)!`)
      
      // Notify parent component about successful upload
      if (this.onUploadSuccess) {
        this.onUploadSuccess()
      }
    }
  }

  showError(message) {
    // You can implement a toast notification system here
    alert(message)
  }

  showSuccess(message) {
    // You can implement a toast notification system here
    alert(message)
  }
}

// Make it globally accessible for the remove button
window.fileUpload = null