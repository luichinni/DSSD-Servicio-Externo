import uuid
from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Recurso(Base):
    __tablename__ = "recursos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    unidad_medida: Mapped[str] = mapped_column(String(50), nullable=False)