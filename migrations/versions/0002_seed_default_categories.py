"""Seed the default civic report categories."""

from alembic import op
from sqlalchemy import Boolean, String, Text, column, table


revision = "0002_seed_default_categories"
down_revision = "0001_core_schema"
branch_labels = None
depends_on = None


categories = table(
    "categoria",
    column("nome", String(100)),
    column("descrizione", Text),
    column("attiva", Boolean),
)

DEFAULT_CATEGORIES = (
    "Accessibilità",
    "Acqua e fognature",
    "Illuminazione",
    "Rifiuti e decoro",
    "Strade e marciapiedi",
    "Verde pubblico",
)


def upgrade():
    op.bulk_insert(
        categories,
        [
            {"nome": name, "descrizione": "Categoria iniziale", "attiva": True}
            for name in DEFAULT_CATEGORIES
        ],
    )


def downgrade():
    # Keep seeded rows to avoid deleting categories that may now be referenced.
    pass
