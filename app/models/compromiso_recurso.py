from datetime import datetime, timezone
import enum

from sqlalchemy import CheckConstraint, DateTime, Enum, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.core.timezone import ahora_ar


class EstadoCompromiso(str, enum.Enum):
    COMPROMETIDO = "COMPROMETIDO"
    LIBERADO = "LIBERADO"


class CompromisoRecurso(Base):
    __tablename__ = "compromisos_recursos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_emergencia: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    id_oferta: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    id_ong: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    id_recurso: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cantidad_comprometida: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[EstadoCompromiso] = mapped_column(
        Enum(
            EstadoCompromiso,
            name="estado_compromiso_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=EstadoCompromiso.COMPROMETIDO,
    )
    fecha_bloqueo: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: ahora_ar(),
        nullable=False,
    )
    fecha_liberacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "id_emergencia",
            "id_oferta",
            "id_ong",
            "id_recurso",
            name="uq_compromiso_emergencia_oferta_ong_recurso",
        ),
        CheckConstraint("cantidad_comprometida > 0", name="chk_compromiso_cantidad_positiva"),
        Index("ix_compromisos_emergencia_ong", "id_emergencia", "id_ong"),
    )

    def __repr__(self) -> str:
        return (
            f"<CompromisoRecurso emergencia={self.id_emergencia} oferta={self.id_oferta} "
            f"ong={self.id_ong} recurso={self.id_recurso} cant={self.cantidad_comprometida} "
            f"estado={self.estado}>"
        )
