# Medical Document RAG (Retrieval-Augmented Generation) System

## Overview

This is a full-stack application that combines a **React frontend** with a **FastAPI backend** to create an intelligent medical document question-answering system. The system uses Retrieval-Augmented Generation (RAG) to provide accurate, context-aware responses based on uploaded PDF documents.

## Key Features

### 🔍 **Intelligent Document Processing**
- **PDF Upload & Processing**: Upload medical documents (PDFs) with automatic text, table, and image extraction
- **Multi-Modal RAG**: Processes text content, tables, and image captions for comprehensive understanding
- **Vector Search**: Uses advanced embedding models specifically trained for medical content (PubMedBERT)

### 🧠 **Smart Query Processing**
- **Intent Classification**: Automatically determines whether questions require document retrieval or can be answered directly
- **Auto Document Selection**: Intelligently selects the most relevant document for each query
- **Conversation Memory**: Maintains chat history with contextual awareness
- **Streaming Responses**: Real-time response streaming for better user experience

### 💬 **Advanced Chat System**
- **Persistent Chat Sessions**: Redis-based chat storage with conversation history
- **Multi-Session Management**: Create, manage, and switch between multiple chat sessions
- **Conversation Context**: Smart context injection that considers previous conversation flow
- **Detailed Logging**: Comprehensive logging of user interactions, document selections, and system performance

### 🏥 **Medical Domain Optimization**
- **Medical LLM**: Specialized language model for medical question-answering
- **Clinical Context Understanding**: Optimized prompt templates for medical scenarios
- **Medical Terminology Support**: Enhanced processing of medical terminology and concepts

## Architecture

### Backend (FastAPI)
```
backend/
├── main.py                    # FastAPI application entry point
├── config.py                  # CORS and app configuration
├── routes.py                  # API endpoints and route handlers
├── rag_pipeline.py           # Core RAG processing logic
├── rag_config.py             # Configuration management
├── models.py                 # Data models and schemas
├── intent_classifier.py     # Query intent classification
├── chat_models.py           # Chat session and message models
├── redis_chat_manager.py    # Redis-based chat persistence
├── chat_logger.py           # Detailed chat event logging
├── upload.py                # PDF upload handling
├── utils.py                 # Utility functions
├── logger_config.py         # Logging configuration
├── redis_cache.py           # Redis caching utilities
└── env_validator.py         # Environment validation
```

### Frontend (React + Vite)
```
frontend/
├── src/
│   ├── App.jsx              # Main application component
│   ├── main.jsx             # React application entry point
│   ├── components/
│   │   ├── Chatbot.jsx      # Main chat interface
│   │   ├── Chatbot.css      # Chat styling
│   │   ├── ChatSidebar.jsx  # Chat session management
│   │   └── ChatSidebar.css  # Sidebar styling
│   └── services/
│       └── api.js           # API communication layer
├── index.html               # HTML template
├── package.json             # Dependencies and scripts
└── vite.config.js          # Vite configuration
```

## Technology Stack

### Backend Technologies
- **FastAPI**: Modern, high-performance web framework
- **MongoDB**: Vector database for embeddings and document storage
- **Redis**: Caching and chat session persistence
- **AWS S3**: Document and metadata storage
- **LangChain**: LLM orchestration and prompt management
- **HuggingFace**: Embedding models and NLP services
- **LM Studio**: Local LLM inference

### Frontend Technologies
- **React 19**: Modern React with latest features
- **Vite**: Fast build tool and development server
- **Axios**: HTTP client for API communication
- **React Markdown**: Advanced markdown rendering with syntax highlighting
- **KaTeX**: Mathematical notation rendering
- **Lucide React**: Modern icon library

### AI/ML Components
- **Embedding Model**: NeuML/pubmedbert-base-embeddings (Medical domain-specific)
- **Language Model**: ii-medical-8b-1706 (Medical-focused LLM)
- **Intent Classifier**: Facebook BART-large-mnli for query classification

## Prerequisites

### System Requirements
- **Node.js** (v16 or higher)
- **Python** (3.8 or higher)
- **Redis** server
- **MongoDB** with vector search capabilities
- **AWS S3** bucket (for document storage)
- **LM Studio** (for local LLM inference)

### Required Environment Variables
Create a `.env` file in the backend directory:

```env
# Required
HUGGINGFACE_API_KEY=your_huggingface_api_key
MONGO_URI=mongodb://your_mongodb_connection_string
OPENAI_API_BASE=http://localhost:1234/v1  # LM Studio endpoint

# Optional (with defaults)
BUCKET=pdf-storage-for-rag-1
EMBEDDING_MODEL=NeuML/pubmedbert-base-embeddings
LLM_MODEL=ii-medical-8b-1706@q4_k_m
SCORE_THRESHOLD=0.75
MAX_CHUNKS=5
LOG_LEVEL=WARNING
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
REDIS_URL=redis://localhost:6379
```

## Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd final
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your actual values
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install
```

### 4. Infrastructure Setup

#### Redis (Docker)
```bash
# Start Redis using Docker Compose
docker-compose up -d redis
```

#### MongoDB
- Set up MongoDB Atlas or local MongoDB instance
- Ensure vector search is enabled
- Create the required indexes for text and image embeddings

#### LM Studio
1. Download and install LM Studio
2. Download the medical model: `ii-medical-8b-1706@q4_k_m`
3. Start the local server on port 1234

## Running the Application

### 1. Start the Backend
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start the Frontend
```bash
cd frontend
npm run dev
```

### 3. Access the Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## API Endpoints

### Core Functionality
- `POST /upload_pdf/` - Upload and process PDF documents
- `POST /auto_ask/` - Ask questions with automatic document selection
- `POST /auto_ask_stream/` - Streaming version of auto_ask
- `GET /list_pdfs/` - List all uploaded documents

### Chat Management
- `POST /chats/` - Create new chat session
- `GET /chats/` - List all chat sessions
- `GET /chats/{chat_id}` - Get specific chat with messages
- `PUT /chats/{chat_id}` - Update chat title
- `DELETE /chats/{chat_id}` - Delete chat session

### Debug & Monitoring
- `GET /health/` - Health check endpoint
- `GET /debug/available_docs/` - Debug available documents
- `GET /chats/{chat_id}/logs` - Get detailed chat logs
- `POST /admin/cleanup-logs` - Clean up old chat logs

## Features in Detail

### 1. Document Processing Pipeline
- **PDF Upload**: Secure file upload with validation (max 50MB, PDF only)
- **Content Extraction**: Extracts text, tables, and image captions
- **Embedding Generation**: Creates vector embeddings for semantic search
- **S3 Storage**: Stores processed content and metadata in AWS S3

### 2. Smart Query Processing
- **Intent Classification**: Determines if queries need document retrieval or direct answers
- **Document Selection**: Automatically selects most relevant document using cosine similarity
- **Context Retrieval**: Fetches relevant text chunks, tables, and images
- **Response Generation**: Uses medical LLM with enriched context

### 3. Chat System
- **Session Management**: Create and manage multiple chat conversations
- **Persistent Storage**: Redis-based storage for chat history
- **Context Awareness**: Maintains conversation context across messages
- **Streaming Interface**: Real-time response streaming

### 4. Monitoring & Logging
- **Comprehensive Logging**: Application logs, error tracking, and performance metrics
- **Chat Analytics**: Detailed logging of user interactions and system decisions
- **Health Monitoring**: Health check endpoints for system status

## Configuration Options

### RAG Pipeline Configuration
```python
# Score threshold for relevance filtering
SCORE_THRESHOLD=0.75

# Maximum number of text chunks to use
MAX_CHUNKS=5

# Document selection parameters
DOC_SELECTION_CHUNKS=30
NORMALIZATION_METHOD=sqrt
MIN_DOCUMENT_CHUNKS=2
MAX_DOCUMENTS_RETURNED=5
```

### Model Configuration
```python
# Embedding model for medical content
EMBEDDING_MODEL=NeuML/pubmedbert-base-embeddings

# Language model for response generation
LLM_MODEL=ii-medical-8b-1706@q4_k_m

# Model temperature for response generation
LLM_TEMPERATURE=0.5
```

## Development

### Code Structure
- **Modular Design**: Separate modules for different functionalities
- **Type Hints**: Comprehensive type annotations throughout
- **Error Handling**: Robust error handling with detailed logging
- **Configuration Management**: Environment-based configuration
- **Caching**: Redis caching for performance optimization

### Testing
```bash
# Run backend tests
cd backend
python -m pytest

# Run frontend tests
cd frontend
npm test
```

### Building for Production
```bash
# Build frontend
cd frontend
npm run build

# The built files will be in the dist/ directory
```

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Ensure Redis is running: `docker-compose up -d redis`
   - Check Redis URL in environment variables

2. **MongoDB Connection Issues**
   - Verify MongoDB URI is correct
   - Ensure vector search indexes are created

3. **LM Studio Connection Issues**
   - Ensure LM Studio is running on port 1234
   - Check that the medical model is loaded

4. **Frontend Build Issues**
   - Clear node_modules: `rm -rf node_modules && npm install`
   - Check Node.js version compatibility

### Debug Mode
Set `LOG_LEVEL=DEBUG` in environment variables for detailed logging.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Commit your changes: `git commit -am 'Add feature'`
5. Push to the branch: `git push origin feature-name`
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **PubMedBERT**: For medical domain-specific embeddings
- **LangChain**: For LLM orchestration
- **FastAPI**: For the high-performance backend framework
- **React**: For the modern frontend framework
- **Medical AI Community**: For domain expertise and model development
