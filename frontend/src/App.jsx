
import React, { useState, useCallback, useMemo } from 'react';
import { FileUpload } from './components/FileUpload.jsx';
import { DocumentSelector } from './components/DocumentSelector.jsx';
import { ChatInterface } from './components/ChatInterface.jsx';
import './App.css';

// Error Boundary Component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('App Error Boundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary" role="alert">
          <div className="error-content">
            <h2>Something went wrong</h2>
            <p>We're sorry, but something unexpected happened. Please refresh the page to try again.</p>
            <button 
              onClick={() => window.location.reload()}
              className="btn-primary"
            >
              Refresh Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

ErrorBoundary.displayName = 'ErrorBoundary';

function App() {
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  const handleUploadSuccess = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
    // Optional: Add success notification here
  }, []);

  const handleSelectionChange = useCallback((newSelection) => {
    setSelectedDocs(newSelection);
  }, []);

  // Memoize selected docs to prevent unnecessary re-renders
  const memoizedSelectedDocs = useMemo(() => selectedDocs, [selectedDocs]);

  const handleGlobalLoading = useCallback((loading) => {
    setIsLoading(loading);
  }, []);

  return (
    <ErrorBoundary>
      <div className="App">
        {/* Skip Navigation Link */}
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>
        
        <header className="App-header" role="banner">
          <h1>Document AI Assistant</h1>
          {isLoading && (
            <div className="global-loading" aria-live="polite">
              <span className="loading-text">Loading...</span>
            </div>
          )}
        </header>
        
        <main id="main-content" role="main">
          <div className="main-layout">
            <aside className="sidebar" role="complementary" aria-label="Document management">
              <section aria-labelledby="upload-section">
                <h2 id="upload-section" className="visually-hidden">File Upload</h2>
                <FileUpload 
                  onUploadSuccess={handleUploadSuccess}
                  onLoadingChange={handleGlobalLoading}
                />
              </section>
              
              <section aria-labelledby="selector-section">
                <h2 id="selector-section" className="visually-hidden">Document Selection</h2>
                <DocumentSelector 
                  onSelectionChange={handleSelectionChange} 
                  refreshTrigger={refreshTrigger}
                  onLoadingChange={handleGlobalLoading}
                />
              </section>
            </aside>
            
            <section className="chat-container" role="region" aria-label="Chat interface">
              <ChatInterface 
                selectedDocs={memoizedSelectedDocs}
                onLoadingChange={handleGlobalLoading}
              />
            </section>
          </div>
        </main>
        
        <footer className="App-footer" role="contentinfo">
          <p>&copy; 2025 Document AI Assistant. All rights reserved.</p>
        </footer>
      </div>
    </ErrorBoundary>
  );
}

export default App;
