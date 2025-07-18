from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

def create_app():
    app = FastAPI()
    
    # Parse ALLOWED_ORIGINS, strip whitespace, and ignore empty entries
    allowed_origins = [origin.strip() for origin in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173"
    ).split(",") if origin.strip()]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        # Allow all standard HTTP methods and preflight
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=600
    )
    return app
