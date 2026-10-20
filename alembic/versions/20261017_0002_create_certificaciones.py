"""Create certificaciones table.

Revision ID: 20261017_0002
Revises: 20261015_0001
"""

from alembic import op
import sqlalchemy as sa

revision = "20261017_0002"
down_revision = "20261015_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "certificaciones",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id_ong", sa.Integer(), nullable=False),
        sa.Column("id_recurso", sa.Integer(), nullable=False),
        sa.Column("tipo_desastre", sa.String(80), nullable=False),
        sa.Column("rol_permitido", sa.String(30), nullable=False),
        sa.Column("riesgo_maximo", sa.String(10), nullable=False),
        sa.Column("perfil_competencia", sa.String(20), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.CheckConstraint("id_ong > 0", name="ck_certificacion_ong_positiva"),
        sa.CheckConstraint("id_recurso > 0", name="ck_certificacion_recurso_positivo"),
        sa.CheckConstraint(
            "rol_permitido IN ('lote_principal', 'apoyo_secundario')",
            name="ck_certificacion_rol",
        ),
        sa.CheckConstraint(
            "riesgo_maximo IN ('bajo', 'medio', 'alto', 'critico')",
            name="ck_certificacion_riesgo",
        ),
        sa.CheckConstraint(
            "perfil_competencia IN ('Basico', 'Intermedio', 'Avanzado')",
            name="ck_certificacion_perfil",
        ),
    )
    op.create_index(
        "ix_certificaciones_ong_recurso", "certificaciones", ["id_ong", "id_recurso"]
    )


def downgrade() -> None:
    op.drop_index("ix_certificaciones_ong_recurso", table_name="certificaciones")
    op.drop_table("certificaciones")
