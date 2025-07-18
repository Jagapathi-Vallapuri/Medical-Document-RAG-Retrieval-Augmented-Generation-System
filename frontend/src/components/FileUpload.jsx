
import React, { useState, useCallback, useMemo, useRef } from 'react';
import { ApiService } from '../services/ApiService';

const apiService = new ApiService();

// Constants
const FILE_CONSTRAINTS = {
  maxSize: 10 * 1024 * 1024, // 10MB
  allowedTypes: [
    'application/pdf',
    'text/plain',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ],
  allowedExtensions: ['.pdf', '.txt', '.doc', '.docx']
};

const FILE_TYPE_CONFIG = {
  'application/pdf': { color: '#dc2626', label: 'PDF Document' },
  'text/plain': { color: '#6b7280', label: 'Text Document' },
  'application/msword': { color: '#2563eb', label: 'Word Document' },
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': { color: '#2563eb', label: 'Word Document' },
  default: { color: '#2563eb', label: 'Document' }
};

// Enhanced file ID generation
const generateFileId = () => {
  return crypto.randomUUID?.() || `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

// Utility to format file size
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// Check for duplicate files
const isDuplicateFile = (newFile, existingFiles) => {
  return existingFiles.some(f => 
    f.name === newFile.name && 
    f.size === newFile.size
  );
};

// Enhanced File Icon Component
const FileIcon = ({ type, status }) => {
  const config = FILE_TYPE_CONFIG[type] || FILE_TYPE_CONFIG.default;
  
  const getIconColor = () => {
    if (status === 'error') return '#ef4444';
    if (status === 'success') return '#10b981';
    return config.color;
  };

  return (
    <div className="file-icon" style={{ color: getIconColor() }}>
      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
      </svg>
    </div>
  );
};

FileIcon.displayName = 'FileIcon';

// Status Icon Component
const StatusIcon = ({ status }) => {
  const getStatusIcon = () => {
    switch (status) {
      case 'pending':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="#6b7280" aria-label="Pending upload">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 6v6l4 2"/>
          </svg>
        );
      case 'uploading':
        return <div className="spinner" aria-label="Uploading file"></div>;
      case 'success':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="#10b981" aria-label="Upload successful">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22,4 12,14.01 9,11.01"/>
          </svg>
        );
      case 'error':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="#ef4444" aria-label="Upload failed">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
        );
      default:
        return null;
    }
  };
  return <div className="file-status">{getStatusIcon()}</div>;
};

StatusIcon.displayName = 'StatusIcon';

// Error Notification Component
const ErrorNotification = ({ errors, onDismiss }) => {
  if (errors.length === 0) return null;

  return (
    <div className="error-notifications" role="alert" aria-live="assertive">
      {errors.map(error => (
        <div key={error.id} className="error-notification">
          <div className="error-content">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="#ef4444" aria-hidden="true">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            <span>{error.message}</span>
          </div>
          <button 
            className="error-dismiss" 
            onClick={() => onDismiss(error.id)}
            aria-label="Dismiss error"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      ))}
    </div>
  );
};

ErrorNotification.displayName = 'ErrorNotification';


export const FileUpload = ({ onUploadSuccess, onLoadingChange }) => {
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [errors, setErrors] = useState([]);
  const [uploadProgress, setUploadProgress] = useState({});
  const fileInputRef = useRef(null);

  // Add error to state
  const addError = useCallback((message, fileId = null) => {
    const error = {
      id: generateFileId(),
      message,
      fileId,
      timestamp: Date.now()
    };
    setErrors(prev => [...prev, error]);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      setErrors(prev => prev.filter(e => e.id !== error.id));
    }, 5000);
  }, []);

  // Dismiss error
  const dismissError = useCallback((errorId) => {
    setErrors(prev => prev.filter(e => e.id !== errorId));
  }, []);

  // Enhanced file validation
  const validateFile = useCallback((file) => {
    if (file.size > FILE_CONSTRAINTS.maxSize) {
      addError(`File "${file.name}" is too large. Maximum size is ${formatFileSize(FILE_CONSTRAINTS.maxSize)}.`);
      return false;
    }
    
    if (!FILE_CONSTRAINTS.allowedTypes.includes(file.type)) {
      addError(`File "${file.name}" is not supported. Please upload ${FILE_CONSTRAINTS.allowedExtensions.join(', ')} files.`);
      return false;
    }
    
    return true;
  }, [addError]);

  const handleFiles = useCallback((files) => {
    const newFiles = Array.from(files).map(file => {
      // Check for duplicates
      if (isDuplicateFile(file, uploadedFiles)) {
        addError(`File "${file.name}" is already selected.`);
        return null;
      }
      
      if (validateFile(file)) {
        return {
          id: generateFileId(),
          file: file,
          name: file.name,
          size: file.size,
          status: 'pending'
        };
      }
      return null;
    }).filter(Boolean); // Filter out nulls from failed validation

    setUploadedFiles(prevFiles => [...prevFiles, ...newFiles]);
  }, [uploadedFiles, addError, validateFile]);

  const removeFile = useCallback((id) => {
    setUploadedFiles(prevFiles => prevFiles.filter(file => file.id !== id));
    setUploadProgress(prev => {
      const newProgress = { ...prev };
      delete newProgress[id];
      return newProgress;
    });
  }, []);

  const clearAllFiles = useCallback(() => {
    setUploadedFiles([]);
    setUploadProgress({});
    setErrors([]);
  }, []);

  // Retry failed upload
  const retryUpload = useCallback(async (fileObj) => {
    setUploadedFiles(prevFiles => 
      prevFiles.map(f => f.id === fileObj.id ? { ...f, status: 'uploading' } : f)
    );
    
    try {
      await apiService.uploadFile(fileObj.file);
      setUploadedFiles(prevFiles => 
        prevFiles.map(f => f.id === fileObj.id ? { ...f, status: 'success' } : f)
      );
    } catch (error) {
      console.error('Retry upload error:', error);
      setUploadedFiles(prevFiles => 
        prevFiles.map(f => f.id === fileObj.id ? { ...f, status: 'error' } : f)
      );
      addError(`Failed to upload "${fileObj.name}". Please try again.`);
    }
  }, [addError]);

  const processAllFiles = useCallback(async () => {
    if (uploadedFiles.length === 0) return;

    setIsProcessing(true);
    if (onLoadingChange) onLoadingChange(true);
    let successCount = 0;
    let errorCount = 0;

    const pendingFiles = uploadedFiles.filter(f => f.status === 'pending' || f.status === 'error');
    
    for (const fileObj of pendingFiles) {
      setUploadedFiles(prevFiles => 
        prevFiles.map(f => f.id === fileObj.id ? { ...f, status: 'uploading' } : f)
      );
      
      try {
        await apiService.uploadFile(fileObj.file);
        setUploadedFiles(prevFiles => 
          prevFiles.map(f => f.id === fileObj.id ? { ...f, status: 'success' } : f)
        );
        successCount++;
      } catch (error) {
        console.error('Upload error:', error);
        setUploadedFiles(prevFiles => 
          prevFiles.map(f => f.id === fileObj.id ? { ...f, status: 'error' } : f)
        );
        addError(`Failed to upload "${fileObj.name}".`);
        errorCount++;
      }
    }

    setIsProcessing(false);
    if (onLoadingChange) onLoadingChange(false);
    
    // Show completion notification
    if (successCount > 0) {
      addError(`Successfully processed ${successCount} file(s)!`);
      if (onUploadSuccess) {
        onUploadSuccess();
      }
    }
    
    if (errorCount > 0) {
      addError(`${errorCount} file(s) failed to upload. Click retry to try again.`);
    }
  }, [uploadedFiles, addError, onUploadSuccess, onLoadingChange]);

  const onDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const onDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const onFileInputChange = useCallback((e) => {
    handleFiles(e.target.files);
    // Reset the input value to allow selecting the same file again
    e.target.value = '';
  }, [handleFiles]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInputRef.current?.click();
    }
  }, []);

  const handleUploadAreaClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  return (
    <div className="file-upload-container">
      <ErrorNotification errors={errors} onDismiss={dismissError} />
      
      <div
        className={`upload-area ${isDragOver ? 'drag-over' : ''}`}
        onClick={handleUploadAreaClick}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        role="button"
        tabIndex={0}
        onKeyDown={handleKeyDown}
        aria-label="Upload files by clicking or dragging"
        aria-describedby="upload-instructions"
      >
        <div className="upload-icon" aria-hidden="true">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-15"/>
            <polyline points="7,10 12,15 17,10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
        </div>
        <div className="upload-text">
          <h4>Drop files here or click to browse</h4>
          <p id="upload-instructions">
            Supports {FILE_CONSTRAINTS.allowedExtensions.join(', ')} files up to {formatFileSize(FILE_CONSTRAINTS.maxSize)}
          </p>
        </div>
        <input 
          type="file" 
          ref={fileInputRef}
          multiple 
          accept={FILE_CONSTRAINTS.allowedExtensions.join(',')} 
          hidden 
          onChange={onFileInputChange}
          aria-label="Select files to upload"
        />
      </div>

      {uploadedFiles.length > 0 && (
        <div className="uploaded-files" role="region" aria-label="Selected files">
          <h4>Selected Files ({uploadedFiles.length})</h4>
          <div className="file-list">
            {uploadedFiles.map(fileObj => (
              <div 
                key={fileObj.id} 
                className={`file-item ${fileObj.status}`} 
                role="listitem"
                aria-label={`${fileObj.name}, ${formatFileSize(fileObj.size)}, status: ${fileObj.status}`}
              >
                <div className="file-info">
                  <FileIcon type={fileObj.file.type} status={fileObj.status} />
                  <div className="file-details">
                    <div className="file-name" title={fileObj.name}>{fileObj.name}</div>
                    <div className="file-size">{formatFileSize(fileObj.size)}</div>
                  </div>
                </div>
                <div className="file-actions">
                  <StatusIcon status={fileObj.status} />
                  {fileObj.status === 'error' && (
                    <button 
                      className="retry-file" 
                      onClick={() => retryUpload(fileObj)}
                      aria-label={`Retry uploading ${fileObj.name}`}
                      title="Retry upload"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="23,4 23,10 17,10"/>
                        <path d="M20.49,9A9,9,0,0,0,5.64,5.64L1,10"/>
                      </svg>
                    </button>
                  )}
                  <button 
                    className="remove-file" 
                    onClick={() => removeFile(fileObj.id)}
                    aria-label={`Remove ${fileObj.name} from upload queue`}
                    title="Remove file"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18"/>
                      <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="upload-actions">
        <button 
          className="btn-secondary" 
          onClick={clearAllFiles}
          disabled={uploadedFiles.length === 0}
          aria-label="Clear all selected files"
        >
          Clear All
        </button>
        <button
          className="btn-primary"
          disabled={uploadedFiles.length === 0 || isProcessing}
          onClick={processAllFiles}
          aria-label={isProcessing ? "Processing files..." : "Process selected files"}
        >
          {isProcessing ? 'Processing...' : 'Process Files'}
        </button>
      </div>
    </div>
  );
};
