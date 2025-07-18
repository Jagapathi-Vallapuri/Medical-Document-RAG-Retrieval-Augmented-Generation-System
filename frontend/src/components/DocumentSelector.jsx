
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { ApiService } from '../services/ApiService';

const apiService = new ApiService();

// Constants for file type colors and icons
const FILE_TYPE_CONFIG = {
    pdf: { color: '#dc2626', label: 'PDF Document' },
    txt: { color: '#6b7280', label: 'Text Document' },
    doc: { color: '#2563eb', label: 'Word Document' },
    docx: { color: '#2563eb', label: 'Word Document' },
    default: { color: '#059669', label: 'Document' }
};

// Enhanced error handling
const getErrorMessage = (error) => {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
        return 'Network connection issue. Please check your internet and try again.';
    }
    if (error.status === 404) {
        return 'Document service is currently unavailable. Please try again later.';
    }
    if (error.status === 403) {
        return 'You don\'t have permission to access documents. Please contact support.';
    }
    if (error.status === 500) {
        return 'Server error occurred. Our team has been notified. Please try again in a few moments.';
    }
    return 'Unable to load your documents. Please try again.';
};

const DocumentIcon = ({ nameOrType, isSelected = false }) => {
    const fileTypeConfig = useMemo(() => {
        const name = nameOrType.toLowerCase();
        
        if (name.includes('.pdf') || nameOrType === 'pdf') {
            return FILE_TYPE_CONFIG.pdf;
        } else if (name.includes('.txt') || nameOrType === 'txt') {
            return FILE_TYPE_CONFIG.txt;
        } else if (name.includes('.doc') || nameOrType === 'doc' || nameOrType === 'docx') {
            return FILE_TYPE_CONFIG.doc;
        }
        return FILE_TYPE_CONFIG.default;
    }, [nameOrType]);

    return (
        <div className="document-icon" title={fileTypeConfig.label}>
            <svg 
                width="20" 
                height="20" 
                viewBox="0 0 24 24" 
                fill="currentColor"
                style={{ color: isSelected ? 'inherit' : fileTypeConfig.color }}
                aria-hidden="true"
                role="img"
            >
                <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
            </svg>
        </div>
    );
};

DocumentIcon.displayName = 'DocumentIcon';

export const DocumentSelector = ({ onSelectionChange, refreshTrigger, onLoadingChange }) => {
    const [documents, setDocuments] = useState([]);
    const [selectedDocument, setSelectedDocument] = useState(null);
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(false);

    const loadDocuments = useCallback(async () => {
        try {
            setError(null);
            setIsLoading(true);
            if (onLoadingChange) onLoadingChange(true);
            const response = await apiService.getDocuments();
            let docs = response.documents || response.pdfs || [];

            if (docs.length > 0 && typeof docs[0] === 'string') {
                docs = docs.map(filename => ({
                    id: filename,
                    name: filename,
                    type: 'pdf',
                    status: 'Ready'
                }));
            }
            setDocuments(docs);
        } catch (err) {
            console.error('Error loading documents:', err);
            setError(getErrorMessage(err));
        } finally {
            setIsLoading(false);
            if (onLoadingChange) onLoadingChange(false);
        }
    }, [onLoadingChange]);

    useEffect(() => {
        loadDocuments();
    }, [loadDocuments, refreshTrigger]);

    const handleSelection = useCallback((docId) => {
        const newSelectedDoc = selectedDocument === docId ? null : docId;
        setSelectedDocument(newSelectedDoc);
        if (onSelectionChange) {
            onSelectionChange(newSelectedDoc ? [newSelectedDoc] : []);
        }
    }, [selectedDocument, onSelectionChange]);

    const handleKeyDown = useCallback((e, docId) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleSelection(docId);
        }
    }, [handleSelection]);

    // Loading State
    if (isLoading) {
        return (
            <div className="document-selector loading">
                <div className="loading-state">
                    <div className="loading-spinner" aria-label="Loading documents">
                        <div className="spinner"></div>
                    </div>
                    <h4>Loading Documents...</h4>
                    <p>Please wait while we fetch your documents</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="document-selector error">
                <div className="error-state">
                    <div className="error-icon" aria-hidden="true">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="#ef4444">
                            <circle cx="12" cy="12" r="10"/>
                            <line x1="15" y1="9" x2="9" y2="15"/>
                            <line x1="9" y1="9" x2="15" y2="15"/>
                        </svg>
                    </div>
                    <h4>Error Loading Documents</h4>
                    <p>{error}</p>
                    <button 
                        className="retry-btn" 
                        onClick={loadDocuments}
                        disabled={isLoading}
                        aria-label="Retry loading documents"
                    >
                        {isLoading ? 'Retrying...' : 'Retry'}
                    </button>
                </div>
            </div>
        );
    }

    if (documents.length === 0) {
        return (
            <div className="document-selector empty">
                <div className="empty-state">
                    <div className="empty-icon" aria-hidden="true">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="#6b7280">
                            <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
                        </svg>
                    </div>
                    <h4>No Documents Available</h4>
                    <p>Upload some documents first to start asking questions</p>
                    <button 
                        className="refresh-btn" 
                        onClick={loadDocuments}
                        aria-label="Refresh document list"
                    >
                        Refresh
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="document-selector">
            <div className="selector-header">
                <h4>Select Document to Query</h4>
                <button 
                    className="refresh-btn-small" 
                    onClick={loadDocuments}
                    disabled={isLoading}
                    aria-label="Refresh document list"
                    title="Refresh document list"
                >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="23,4 23,10 17,10"/>
                        <polyline points="1,20 1,14 7,14"/>
                        <path d="M20.49,9A9,9,0,0,0,5.64,5.64L1,10"/>
                        <path d="M3.51,15a9,9,0,0,0,14.85,3.36L23,14"/>
                    </svg>
                </button>
            </div>
            <div 
                className="document-list" 
                role="radiogroup" 
                aria-label="Available documents"
                id="documentList"
            >
                {documents.map(doc => (
                    <div
                        key={doc.id}
                        className={`document-item ${selectedDocument === doc.id ? 'selected' : ''}`}
                        onClick={() => handleSelection(doc.id)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => handleKeyDown(e, doc.id)}
                        aria-label={`Select document ${doc.name}`}
                        aria-pressed={selectedDocument === doc.id}
                        aria-describedby={`status-${doc.id}`}
                    >
                        <div className="document-checkbox">
                            <input
                                type="radio"
                                name="document-selection"
                                id={`doc-${doc.id}`}
                                checked={selectedDocument === doc.id}
                                onChange={() => handleSelection(doc.id)}
                                aria-label={`Select ${doc.name}`}
                            />
                            <label htmlFor={`doc-${doc.id}`}></label>
                        </div>
                        <div className="document-info">
                            <DocumentIcon 
                                nameOrType={doc.type || doc.name} 
                                isSelected={selectedDocument === doc.id}
                            />
                            <div className="document-details">
                                <div className="document-name" title={doc.name}>{doc.name}</div>
                            </div>
                        </div>
                        <div className="document-status">
                            <span 
                                className={`status-badge ${doc.status || 'processed'}`}
                                id={`status-${doc.id}`}
                                aria-label={`Status: ${doc.status || 'Ready'}`}
                            >
                                {doc.status || 'Ready'}
                            </span>
                        </div>
                    </div>
                ))}
            </div>
            <div className="selection-summary" role="status" aria-live="polite">
                <span className="selected-count">
                    {selectedDocument ? '1 document selected' : 'No document selected'}
                </span>
            </div>
        </div>
    );
};
