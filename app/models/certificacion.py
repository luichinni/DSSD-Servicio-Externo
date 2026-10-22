from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Certificacion(Base):
    __tablename__ = "certificaciones"
    __table_args__ = (
        CheckConstraint("id_ong > 0", name="ck_certificacion_ong_positiva"),
        CheckConstraint("id_recurso > 0", name="ck_certificacion_recurso_positivo"),
        CheckConstraint(
            "rol_permitido IN ('lote_principal', 'apoyo_secundario')",
            name="ck_certificacion_rol",
        ),
        CheckConstraint(
            "riesgo_maximo IN ('bajo', 'medio', 'alto', 'critico')",
            name="ck_certificacion_riesgo",
        ),
        CheckConstraint(
            "perfil_competencia IN ('Basico', 'Intermedio', 'Avanzado')",
            name="ck_certificacion_perfil",
        ),
        Index("ix_certificaciones_ong_recurso", "id_ong", "id_recurso"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_ong: Mapped[int] = mapped_column(ForeignKey("ongs.id"), nullable=False)
    id_recurso: Mapped[int] = mapped_column(ForeignKey("recursos.id"), nullable=False)
    tipo_desastre: Mapped[str] = mapped_column(String(80), nullable=False)
    rol_permitido: Mapped[str] = mapped_column(String(30), nullable=False)
    riesgo_maximo: Mapped[str] = mapped_column(String(10), nullable=False)
    perfil_competencia: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
