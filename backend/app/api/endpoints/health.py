from fastapi import APIRouter
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Service Health Check")
async def health_check() -> HealthResponse:
    """Returns the operational status of the MoieRec API service."""
    return HealthResponse(status="ok", service="MoieRec API")
