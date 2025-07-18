from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

def create_app():
    app = FastAPI()
    
    # Configure CORS based on environment
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    return app
