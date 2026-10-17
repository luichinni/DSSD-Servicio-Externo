from sqlalchemy import Boolean, Text, String, Mapped, mapped_column
from app.db.base import Base

class ONG(Base):
    __tablename__ = "ongs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    habilitada: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)