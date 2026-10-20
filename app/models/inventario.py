import uuid
from sqlalchemy import Integer, ForeignKey, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Inventario(Base):
    __tablename__ = "inventario"
    __table_args__ = (UniqueConstraint("ong_id", "recurso_id", name="uq_inventario_ong_recurso"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ong_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("ongs.id"), nullable=False, index=True)
    recurso_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("recursos.id"), nullable=False, index=True)
    cantidad_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cantidad_disponible: Mapped[int] = mapped_column(Integer, nullable=False, default=0)