from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.deserializer import deserializar_json_string
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.adjudicacion import AdjudicarRequest, AdjudicarResponse
from app.schemas.auth import ErrorResponse
from app.services.adjudicacion import procesar_adjudicacion

router = APIRouter(
    prefix="/api/v1/ofertas",
    tags=["ofertas"],
    dependencies=[Depends(get_current_user)],
)

adjudicar_responses = {
    401: {
        "model": ErrorResponse,
        "description": "Token JWT inválido o expirado.",
    },
    409: {
        "description": "Conflicto: No se pudo adjudicar ninguna oferta por falta de stock o inconsistencias.",
    },
}


@router.post(
    "/adjudicar",
    response_model=AdjudicarResponse,
    status_code=status.HTTP_200_OK,
    responses=adjudicar_responses,
)
async def adjudicar_ofertas_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    raw_body = await request.body()
    try:
        data = deserializar_json_string(raw_body)
        payload = AdjudicarRequest.model_validate(data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error al deserializar payload JSON de Bonita: {exc}",
        ) from exc

    respuesta, _ = procesar_adjudicacion(db=db, request=payload)
    return Response(
        content=respuesta.model_dump_json(),
        media_type="application/json",
        status_code=status.HTTP_200_OK,
    )
