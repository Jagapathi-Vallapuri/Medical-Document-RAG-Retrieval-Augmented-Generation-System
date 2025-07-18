# Frontend - Document AI Assistant

A modern React-based web application that provides an AI-powered chat interface for document analysis and querying.

## 🚀 Features

- **Drag & Drop File Upload**: Easy document upload with progress tracking
- **Real-time Chat Interface**: Interactive AI chat with typing indicators
- **Document Management**: Select and manage uploaded documents
- **Markdown Support**: Rich text rendering with security sanitization
- **Accessibility**: Full WCAG compliance with screen reader support
- **Error Handling**: Comprehensive error boundaries and user feedback
- **Responsive Design**: Works on desktop and mobile devices

## 🛠 Tech Stack

- **React 19** - Modern React with hooks
- **Vite** - Fast build tool and dev server
- **Marked.js** - Markdown parsing
- **DOMPurify** - XSS protection
- **ESLint** - Code linting

## 📦 Installation

```bash
# Install dependencies
npm install

# Set up environment variables
cp .env.example .env

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 🔧 Environment Variables

Create a `.env` file based on `.env.example`:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_NODE_ENV=development
```

## 🏗 Project Structure

```
src/
├── components/           # React components
│   ├── FileUpload.jsx   # File upload with drag & drop
│   ├── DocumentSelector.jsx # Document selection interface
│   └── ChatInterface.jsx # AI chat interface
├── services/            # API and external services
│   └── ApiService.js    # Backend API communication
├── utils/               # Utility functions
│   └── markdown.js      # Markdown processing with security
├── App.jsx             # Main application component
├── main.jsx            # Application entry point
└── *.css               # Styling files
```

## 🔒 Security Features

- **XSS Prevention**: All user input sanitized with DOMPurify
- **Content Security**: Safe markdown rendering
- **URL Validation**: Links validated before rendering
- **Error Boundaries**: Graceful error handling

## ♿ Accessibility Features

- **Keyboard Navigation**: Full keyboard support
- **Screen Reader Support**: ARIA labels and live regions
- **Focus Management**: Proper focus handling
- **Skip Navigation**: Skip to main content link
- **High Contrast Support**: Works with high contrast modes

## 🎨 Component API

### FileUpload
```jsx
<FileUpload 
  onUploadSuccess={() => {}} 
  onLoadingChange={(loading) => {}} 
/>
```

### DocumentSelector
```jsx
<DocumentSelector 
  onSelectionChange={(docs) => {}} 
  refreshTrigger={number}
  onLoadingChange={(loading) => {}} 
/>
```

### ChatInterface
```jsx
<ChatInterface 
  selectedDocs={['doc1', 'doc2']} 
  onLoadingChange={(loading) => {}} 
/>
```

## 🚀 Performance Optimizations

- **React.memo**: Optimized re-renders for heavy components
- **useCallback**: Memoized event handlers
- **useMemo**: Cached expensive computations
- **Code Splitting**: Lazy loading for large components
- **Error Boundaries**: Prevent crashes from component errors

## 🧪 Development

```bash
# Run linting
npm run lint

# Fix linting errors
npm run lint -- --fix

# Type checking (if using TypeScript)
npm run type-check
```

## 📈 Recent Improvements

- ✅ Fixed prop interface inconsistencies
- ✅ Added environment variable configuration
- ✅ Improved loading state management
- ✅ Enhanced security in markdown processing
- ✅ Optimized callback functions with useCallback
- ✅ Added comprehensive error handling
- ✅ Improved accessibility features

## 🤝 Contributing

1. Follow the existing code style
2. Add proper prop types or TypeScript types
3. Include accessibility features
4. Test thoroughly before submitting
5. Update documentation as needed

## 🐛 Known Issues

- None currently identified

## 📝 License

This project is part of the Document AI Assistant system.
