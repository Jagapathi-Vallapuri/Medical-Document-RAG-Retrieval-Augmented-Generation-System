from fastapi import FastAPI
from config import create_app
from routes import router
from logger_config import setup_logging
import os

# Set up logging before anything else
log_level = os.getenv('LOG_LEVEL', 'WARNING')  # Default to WARNING to reduce console output
setup_logging(log_level=log_level, log_file='logs/app.log')

app = create_app()
app.include_router(router)