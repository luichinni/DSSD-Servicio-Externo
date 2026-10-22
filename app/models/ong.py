from sqlalchemy import Boolean, CheckConstraint, Text, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class ONG(Base):
    __tablename__ = "ongs"
    __table_args__ = (CheckConstraint("id > 0", name="ck_ongs_id_positivo"),)

    # El alta proporciona el ID de la app local; no se genera otro ID independiente.
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    habilitada: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
