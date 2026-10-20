"""Create national catalogs and link existing certifications without deleting data."""

from alembic import op
import sqlalchemy as sa

revision = "20261020_0003"
down_revision = "20261017_0002"
branch_labels = None
depends_on = None

PENDIENTE = "Referencia heredada de certificaciones; completar y verificar antes de habilitar."


def upgrade() -> None:
    op.create_table(
        "ongs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("habilitada", sa.Boolean(), nullable=False),
        sa.CheckConstraint("id > 0", name="ck_ongs_id_positivo"),
    )
    op.create_table(
        "recursos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("unidad_medida", sa.String(50), nullable=False),
        sa.CheckConstraint("id > 0", name="ck_recursos_id_positivo"),
        sa.UniqueConstraint("nombre", name="uq_recursos_nombre"),
    )
    op.create_table(
        "inventario",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("ong_id", sa.Integer(), sa.ForeignKey("ongs.id"), nullable=False),
        sa.Column("recurso_id", sa.Integer(), sa.ForeignKey("recursos.id"), nullable=False),
        sa.Column("cantidad_total", sa.Integer(), nullable=False),
        sa.Column("cantidad_disponible", sa.Integer(), nullable=False),
        sa.UniqueConstraint("ong_id", "recurso_id", name="uq_inventario_ong_recurso"),
        sa.CheckConstraint("cantidad_total >= 0", name="ck_inventario_total_no_negativo"),
        sa.CheckConstraint(
            "cantidad_disponible >= 0 AND cantidad_disponible <= cantidad_total",
            name="ck_inventario_disponible_valido",
        ),
    )
    op.create_index("ix_inventario_ong_id", "inventario", ["ong_id"])
    op.create_index("ix_inventario_recurso_id", "inventario", ["recurso_id"])

    # Las versiones anteriores permitían certificados sin catálogo. Conservarlos
    # creando referencias pendientes; su existencia no acredita habilitación.
    certificados = sa.table("certificaciones", sa.column("id_ong"), sa.column("id_recurso"))
    ongs = sa.table("ongs", sa.column("id"), sa.column("nombre"), sa.column("descripcion"), sa.column("habilitada"))
    recursos = sa.table("recursos", sa.column("id"), sa.column("nombre"), sa.column("unidad_medida"))
    conexion = op.get_bind()
    conexion.execute(ongs.insert().from_select(
        ["id", "nombre", "descripcion", "habilitada"],
        sa.select(
            certificados.c.id_ong,
            sa.literal("ONG pendiente #") + sa.cast(certificados.c.id_ong, sa.String()),
            sa.literal(PENDIENTE), sa.false(),
        ).distinct(),
    ))
    conexion.execute(recursos.insert().from_select(
        ["id", "nombre", "unidad_medida"],
        sa.select(
            certificados.c.id_recurso,
            sa.literal("Recurso pendiente #") + sa.cast(certificados.c.id_recurso, sa.String()),
            sa.literal("unidad"),
        ).distinct(),
    ))
    with op.batch_alter_table("certificaciones") as batch:
        batch.create_foreign_key("fk_certificaciones_ong", "ongs", ["id_ong"], ["id"])
        batch.create_foreign_key("fk_certificaciones_recurso", "recursos", ["id_recurso"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("certificaciones") as batch:
        batch.drop_constraint("fk_certificaciones_recurso", type_="foreignkey")
        batch.drop_constraint("fk_certificaciones_ong", type_="foreignkey")
    op.drop_index("ix_inventario_recurso_id", table_name="inventario")
    op.drop_index("ix_inventario_ong_id", table_name="inventario")
    op.drop_table("inventario")
    op.drop_table("recursos")
    op.drop_table("ongs")
