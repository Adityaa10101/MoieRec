from fastapi import APIRouter
from app.api.endpoints import health

api_router = APIRouter()

# Include health routes under /api
api_router.include_router(health.router, tags=["Health"])
