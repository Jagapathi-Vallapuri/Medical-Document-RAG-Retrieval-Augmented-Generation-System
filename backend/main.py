from fastapi import FastAPI
from config import create_app
from routes import router
from logger_config import setup_logging
import os

# Set up logging before anything else
log_level = os.getenv('LOG_LEVEL', 'WARNING')  
setup_logging(log_level=log_level, log_file='logs/app.log')

app = create_app()
app.include_router(router)

@app.on_event("shutdown")
def shutdown_pipeline():
    """Close RAGPipeline singleton on application shutdown"""
    try:
        from routes import pipeline
        pipeline.close()
    except Exception:
        pass