from fastapi import FastAPI
from config import create_app
from routes import router

app = create_app()
app.include_router(router)