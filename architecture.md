
```mermaid
graph TD
    subgraph User
        U[<fa:fa-user> User]
    end

    subgraph Frontend [Frontend (React + Vite)]
        style Frontend fill:#e6f7ff,stroke:#91d5ff,stroke-width:2px
        FE_UI[<fa:fa-window-maximize> Chat UI]
        FE_API[<fa:fa-paper-plane> api.js]
        FE_UI --> FE_API
    end

    subgraph Backend [Backend (FastAPI)]
        style Backend fill:#f6ffed,stroke:#b7eb8f,stroke-width:2px
        B_Router[<fa:fa-route> API Routes]
        B_RAG[<fa:fa-cogs> RAG Pipeline]
        B_Intent[<fa:fa-lightbulb> Intent Classifier]
        B_Upload[<fa:fa-upload> PDF Uploader]
        B_Chat[<fa:fa-comments> Chat Manager]

        B_Router --> B_Intent
        B_Router --> B_RAG
        B_Router --> B_Upload
        B_Router --> B_Chat
    end

    subgraph DataStores [Data & Caching]
        style DataStores fill:#fffbe6,stroke:#ffe58f,stroke-width:2px
        DB_Mongo[<fa:fa-database> MongoDB<br>(Vector Store for Text/Image Embeddings)]
        DB_Redis[<fa:fa-database> Redis<br>(Cache & Chat Session Storage)]
        DB_S3[<fa:fa-aws> AWS S3<br>(Raw PDFs, Extracted Tables/Images)]
    end

    subgraph AI_Services [AI/ML Services]
        style AI_Services fill:#f9f0ff,stroke:#d3adf7,stroke-width:2px
        AI_HF[<fa:fa-brain> Hugging Face API<br>(PubMedBERT Embedding Model)]
        AI_LMStudio[<fa:fa-robot> LM Studio<br>(Medical LLM Server)]
    end

    %% --- Main Flows ---

    %% PDF Upload Flow
    U -- 1. Uploads PDF --> FE_UI
    FE_API -- 2. POST /upload_pdf --> B_Upload
    B_Upload -- 3. Stores original file --> DB_S3
    B_Upload -- 4. Triggers processing --> B_RAG
    B_RAG -- 5. Extracts text, tables, images --> DB_S3
    B_RAG -- 6. Generates embeddings --> AI_HF
    B_RAG -- 7. Stores embeddings --> DB_Mongo

    %% RAG Query Flow
    U -- "A. Asks a question" --> FE_UI
    FE_API -- "B. POST /auto_ask_stream" --> B_Router
    B_Intent -- "C. Classifies intent as 'retrieval'" --> B_RAG
    B_RAG -- "D. Finds relevant document chunks" --> DB_Mongo
    B_RAG -- "E. Fetches tables/images from cache" --> DB_Redis
    DB_Redis -- "F. Cache miss, fetches from S3" --> DB_S3
    B_RAG -- "G. Builds prompt with context" --> AI_LMStudio
    AI_LMStudio -- "H. Generates response" --> B_RAG
    B_RAG -- "I. Streams response back" --> B_Router
    B_Router -- "J. Saves conversation" --> B_Chat
    B_Chat -- "K. Persists chat" --> DB_Redis
    B_Router -- "L. Streams to client" --> FE_API
    FE_API -- "M. Displays answer" --> FE_UI

```
