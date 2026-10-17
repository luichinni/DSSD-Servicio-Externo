from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InventarioNacional(Base):
    __tablename__ = "inventario_nacional"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_ong: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    id_recurso: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cantidad_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cantidad_disponible: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("id_ong", "id_recurso", name="uq_inventario_ong_recurso"),
        CheckConstraint("cantidad_disponible >= 0", name="chk_inventario_disponible_no_negativo"),
        CheckConstraint(
            "cantidad_disponible <= cantidad_total",
            name="chk_inventario_disponible_no_mayor_total",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<InventarioNacional ong={self.id_ong} recurso={self.id_recurso} "
            f"({self.cantidad_disponible}/{self.cantidad_total})>"
        )
