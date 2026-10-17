from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.ofertas import router as ofertas_router
from app.api.routes.proyectos import router as proyectos_router

__all__ = ["auth_router", "health_router", "ofertas_router", "proyectos_router"]