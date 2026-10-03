from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Current health status of the service")
    service: str = Field(default="MoieRec API", description="Name of the API service")
