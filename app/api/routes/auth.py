from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.openapi import TAG_AUTH
from app.core.security import (
    create_access_token,
    get_current_user,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.schemas.errors import ErrorResponse

router = APIRouter(prefix="/auth", tags=[TAG_AUTH])
unauthorized_response = {
    401: {
        "model": ErrorResponse,
        "description": "Credenciales incorrectas o token inválido/expirado.",
        "headers": {"WWW-Authenticate": {"schema": {"type": "string"}}},
    }
}


@router.post(
    "/login",
    response_model=TokenResponse,
    responses=unauthorized_response,
    summary="Iniciar sesión y obtener token JWT",
    description="Autentica las credenciales (email y contraseña) y emite un token de acceso Bearer JWT válido para los endpoints protegidos.",
)
def login(
    credentials: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    user = db.scalar(
        select(User).where(User.email == str(credentials.email).lower())
    )
    valid_credentials = user is not None and verify_password(
        credentials.password, user.hashed_password
    )
    if not valid_credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(access_token=create_access_token(user.id))


@router.get(
    "/me",
    response_model=UserResponse,
    responses=unauthorized_response,
)
def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse.model_validate(current_user)
