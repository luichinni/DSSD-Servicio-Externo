import logging

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.routes import auth_router, health_router
from app.core.config import DatabaseConfigurationError, JWTConfigurationError

app = FastAPI(title="DSSD Servicio Externo API")

app.include_router(health_router)
app.include_router(auth_router)


def custom_openapi() -> dict:
    if app.openapi_schema is not None:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )
    security_schemes = schema.get("components", {}).get("securitySchemes", {})
    for name, scheme in security_schemes.items():
        if scheme.get("type") == "oauth2":
            security_schemes[name] = {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


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


@app.exception_handler(JWTConfigurationError)
async def jwt_configuration_error_handler(
    request: Request,
    exc: JWTConfigurationError,
) -> JSONResponse:
    logging.getLogger(__name__).error("%s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Authentication is not configured"},
    )
