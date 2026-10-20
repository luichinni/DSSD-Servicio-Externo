from sqlalchemy import Boolean, Text, String, Mapped, mapped_column, Uuid
from app.db.base import Base
import uuid

class ONG(Base):
    __tablename__ = "ongs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    habilitada: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)