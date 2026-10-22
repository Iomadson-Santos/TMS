"""Cria as tabelas iniciais do TMS.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-19
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("administrador", "operador", "motorista", name="user_role", native_enum=False, create_constraint=False), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "vehicles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plate", sa.String(length=10), nullable=False),
        sa.Column("brand", sa.String(length=80), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("capacity_kg", sa.Numeric(12, 2), nullable=True),
        sa.Column("capacity_m3", sa.Numeric(12, 3), nullable=True),
        sa.Column("current_km", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.Enum("disponivel", "em_rota", "manutencao", "inativo", name="vehicle_status", native_enum=False, create_constraint=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vehicles_plate", "vehicles", ["plate"], unique=True)
    op.create_index("ix_vehicles_status", "vehicles", ["status"])

    op.create_table(
        "routes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("vehicle_id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("aberta", "em_andamento", "concluida", "cancelada", name="route_status", native_enum=False, create_constraint=False), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("distance_km", sa.Numeric(12, 2), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.ForeignKeyConstraint(["driver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
    )
    op.create_index("ix_routes_name", "routes", ["name"])
    op.create_index("ix_routes_status", "routes", ["status"])
    op.create_index("ix_routes_vehicle_id", "routes", ["vehicle_id"])
    op.create_index("ix_routes_driver_id", "routes", ["driver_id"])

    op.create_table(
        "deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_number", sa.String(length=60), nullable=False),
        sa.Column("customer_name", sa.String(length=180), nullable=False),
        sa.Column("customer_document", sa.String(length=30), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("postal_code", sa.String(length=12), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("weight_kg", sa.Numeric(12, 2), nullable=True),
        sa.Column("volume_m3", sa.Numeric(12, 3), nullable=True),
        sa.Column("invoice_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("freight_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("status", sa.Enum("recebida", "separada", "faturada", "pendente", "em_rota", "entregue", "devolvida", "cancelada", name="delivery_status", native_enum=False, create_constraint=False), nullable=False),
        sa.Column("route_id", sa.Integer(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"]),
    )
    op.create_index("ix_deliveries_invoice_number", "deliveries", ["invoice_number"])
    op.create_index("ix_deliveries_customer_name", "deliveries", ["customer_name"])
    op.create_index("ix_deliveries_customer_document", "deliveries", ["customer_document"])
    op.create_index("ix_deliveries_city", "deliveries", ["city"])
    op.create_index("ix_deliveries_state", "deliveries", ["state"])
    op.create_index("ix_deliveries_status", "deliveries", ["status"])
    op.create_index("ix_deliveries_route_id", "deliveries", ["route_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=80), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("deliveries")
    op.drop_table("routes")
    op.drop_table("vehicles")
    op.drop_table("users")
