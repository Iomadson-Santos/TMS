"""Adiciona rastreamento e garante uma rota ativa por motorista.

Revision ID: 0002_tracking
Revises: 0001_initial
Create Date: 2026-07-19
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002_tracking"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _index_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {item["name"] for item in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "tracking_positions" not in tables:
        op.create_table(
            "tracking_positions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("driver_id", sa.Integer(), nullable=False),
            sa.Column("route_id", sa.Integer(), nullable=False),
            sa.Column("vehicle_id", sa.Integer(), nullable=False),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("accuracy_m", sa.Float(), nullable=True),
            sa.Column("speed_kmh", sa.Float(), nullable=True),
            sa.Column("heading", sa.Float(), nullable=True),
            sa.Column("altitude_m", sa.Float(), nullable=True),
            sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("source", sa.String(length=30), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["driver_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["route_id"], ["routes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        )

    tracking_indexes = _index_names("tracking_positions")
    simple_indexes = {
        "ix_tracking_positions_driver_id": ["driver_id"],
        "ix_tracking_positions_route_id": ["route_id"],
        "ix_tracking_positions_vehicle_id": ["vehicle_id"],
        "ix_tracking_positions_captured_at": ["captured_at"],
        "ix_tracking_positions_route_created": ["route_id", "created_at"],
        "ix_tracking_positions_driver_created": ["driver_id", "created_at"],
    }
    for name, columns in simple_indexes.items():
        if name not in tracking_indexes:
            op.create_index(name, "tracking_positions", columns)

    duplicate_drivers = bind.execute(
        sa.text(
            """
            SELECT driver_id, COUNT(*) AS total
            FROM routes
            WHERE status = 'em_andamento' AND driver_id IS NOT NULL
            GROUP BY driver_id
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    if duplicate_drivers:
        ids = ", ".join(str(row[0]) for row in duplicate_drivers)
        raise RuntimeError(
            "Nao foi possivel ativar a regra de rota unica. "
            f"Motoristas com mais de uma rota em andamento: {ids}"
        )

    duplicate_vehicles = bind.execute(
        sa.text(
            """
            SELECT vehicle_id, COUNT(*) AS total
            FROM routes
            WHERE status = 'em_andamento'
            GROUP BY vehicle_id
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    if duplicate_vehicles:
        ids = ", ".join(str(row[0]) for row in duplicate_vehicles)
        raise RuntimeError(
            "Nao foi possivel ativar a regra de veiculo unico. "
            f"Veiculos com mais de uma rota em andamento: {ids}"
        )

    route_indexes = _index_names("routes")
    if "uq_routes_driver_in_progress" not in route_indexes:
        op.create_index(
            "uq_routes_driver_in_progress",
            "routes",
            ["driver_id"],
            unique=True,
            sqlite_where=sa.text("status = 'em_andamento' AND driver_id IS NOT NULL"),
            postgresql_where=sa.text("status = 'em_andamento' AND driver_id IS NOT NULL"),
        )
    if "uq_routes_vehicle_in_progress" not in route_indexes:
        op.create_index(
            "uq_routes_vehicle_in_progress",
            "routes",
            ["vehicle_id"],
            unique=True,
            sqlite_where=sa.text("status = 'em_andamento'"),
            postgresql_where=sa.text("status = 'em_andamento'"),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "routes" in tables:
        route_indexes = _index_names("routes")
        if "uq_routes_vehicle_in_progress" in route_indexes:
            op.drop_index("uq_routes_vehicle_in_progress", table_name="routes")
        if "uq_routes_driver_in_progress" in route_indexes:
            op.drop_index("uq_routes_driver_in_progress", table_name="routes")

    if "tracking_positions" in tables:
        op.drop_table("tracking_positions")
