from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.deserializer import deserializar_json_string
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import ErrorResponse
from app.schemas.liberacion import LiberarRequest, LiberarResponse
from app.services.liberacion import procesar_liberacion

router = APIRouter(
    prefix="/api/v1/proyectos",
    tags=["proyectos"],
    dependencies=[Depends(get_current_user)],
)

liberar_responses = {
    401: {
        "model": ErrorResponse,
        "description": "Token JWT inválido o expirado.",
    },
    404: {
        "description": "No se encontraron recursos comprometidos activos para la emergencia y ONG indicadas.",
    },
}


@router.post(
    "/liberar-recursos",
    response_model=LiberarResponse,
    status_code=status.HTTP_200_OK,
    responses=liberar_responses,
)
async def liberar_recursos_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    raw_body = await request.body()
    try:
        data = deserializar_json_string(raw_body)
        payload = LiberarRequest.model_validate(data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error al deserializar payload JSON de Bonita: {exc}",
        ) from exc

    respuesta = procesar_liberacion(db=db, request=payload)
    return Response(
        content=respuesta.model_dump_json(),
        media_type="application/json",
        status_code=status.HTTP_200_OK,
    )
