"""Create compromisos_recursos table.

Revision ID: 20261021_0004
Revises: 20261020_0003
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261021_0004"
down_revision: Union[str, None] = "20261020_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "compromisos_recursos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_emergencia", sa.Integer(), nullable=False),
        sa.Column("id_oferta", sa.Integer(), nullable=False),
        sa.Column("id_ong", sa.Integer(), nullable=False),
        sa.Column("id_recurso", sa.Integer(), nullable=False),
        sa.Column("cantidad_comprometida", sa.Integer(), nullable=False),
        sa.Column(
            "estado",
            sa.Enum(
                "COMPROMETIDO",
                "LIBERADO",
                name="estado_compromiso_enum",
            ),
            nullable=False,
            server_default="COMPROMETIDO",
        ),
        sa.Column("fecha_bloqueo", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_liberacion", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id_emergencia",
            "id_oferta",
            "id_ong",
            "id_recurso",
            name="uq_compromiso_emergencia_oferta_ong_recurso",
        ),
        sa.CheckConstraint("cantidad_comprometida > 0", name="chk_compromiso_cantidad_positiva"),
    )
    op.create_index("ix_compromisos_recursos_id_emergencia", "compromisos_recursos", ["id_emergencia"])
    op.create_index("ix_compromisos_recursos_id_oferta", "compromisos_recursos", ["id_oferta"])
    op.create_index("ix_compromisos_recursos_id_ong", "compromisos_recursos", ["id_ong"])
    op.create_index("ix_compromisos_recursos_id_recurso", "compromisos_recursos", ["id_recurso"])
    op.create_index(
        "ix_compromisos_emergencia_ong",
        "compromisos_recursos",
        ["id_emergencia", "id_ong"],
    )


def downgrade() -> None:
    op.drop_index("ix_compromisos_emergencia_ong", table_name="compromisos_recursos")
    op.drop_index("ix_compromisos_recursos_id_recurso", table_name="compromisos_recursos")
    op.drop_index("ix_compromisos_recursos_id_ong", table_name="compromisos_recursos")
    op.drop_index("ix_compromisos_recursos_id_oferta", table_name="compromisos_recursos")
    op.drop_index("ix_compromisos_recursos_id_emergencia", table_name="compromisos_recursos")
    op.drop_table("compromisos_recursos")
    sa.Enum(name="estado_compromiso_enum").drop(op.get_bind(), checkfirst=True)
