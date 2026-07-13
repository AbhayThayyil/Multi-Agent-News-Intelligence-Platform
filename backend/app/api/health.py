from fastapi import APIRouter, Depends

from app.config.settings import Settings, get_settings
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", environment=settings.app_env)
