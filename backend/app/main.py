from fastapi import FastAPI

from app.api.health import router as health_router

app = FastAPI(title="Multi-Agent News Intelligence Platform")

app.include_router(health_router)
