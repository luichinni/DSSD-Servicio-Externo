from sqlalchemy import CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Recurso(Base):
    __tablename__ = "recursos"
    __table_args__ = (
        CheckConstraint("id > 0", name="ck_recursos_id_positivo"),
        UniqueConstraint("nombre", name="uq_recursos_nombre"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    unidad_medida: Mapped[str] = mapped_column(String(50), nullable=False)
