"""FastAPI application entrypoint."""

from dotenv import load_dotenv
from fastapi import FastAPI

from app.adapters.inbound.http.routes import router

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Kavak AI Sales Agent",
    description="AI-powered sales agent using Clean Architecture",
    version="0.1.0",
)

app.include_router(router)
