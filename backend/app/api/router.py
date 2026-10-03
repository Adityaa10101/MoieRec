from fastapi import APIRouter
from app.api.endpoints import health
from app.api.endpoints import movies

api_router = APIRouter()

# Include health routes under /api
api_router.include_router(health.router, tags=["Health"])

# Include movie routes under /api
api_router.include_router(movies.router, tags=["Movies"])
