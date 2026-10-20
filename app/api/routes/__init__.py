from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.ofertas import router as ofertas_router
from app.api.routes.ongs import router as ongs_router

__all__ = ["auth_router", "health_router", "ofertas_router", "ongs_router"]
