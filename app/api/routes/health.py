import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.openapi import TAG_HEALTH
from app.db.session import get_db
from app.schemas.health import HealthResponse

router = APIRouter(tags=[TAG_HEALTH])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/health/db",
    response_model=HealthResponse,
    responses={
        503: {
            "description": "La base de datos no está disponible.",
            "content": {
                "application/json": {
                    "example": {"detail": "Database unavailable"}
                }
            },
        }
    },
)
def database_health_check(
    db: Annotated[Session, Depends(get_db)],
) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.exception("Database health check failed")
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from exc

    return HealthResponse(status="ok")
