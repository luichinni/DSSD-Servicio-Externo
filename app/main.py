import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.core.config import DatabaseConfigurationError

app = FastAPI(title="DSSD Servicio Externo API")

app.include_router(health_router)


@app.exception_handler(DatabaseConfigurationError)
async def database_configuration_error_handler(
    request: Request,
    exc: DatabaseConfigurationError,
) -> JSONResponse:
    logging.getLogger(__name__).error("%s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database unavailable"},
    )
