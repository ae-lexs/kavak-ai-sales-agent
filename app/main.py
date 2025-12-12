"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.adapters.inbound.http.routes import router

app = FastAPI(
    title="Kavak AI Sales Agent",
    description="AI-powered sales agent using Clean Architecture",
    version="0.1.0",
)

app.include_router(router)

