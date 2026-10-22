"""Adiciona controles de sessao e limite de tentativas de login.

Revision ID: 0003_security
Revises: 0002_tracking
Create Date: 2026-07-20
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_security"
down_revision: str | None = "0002_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    user_columns = {item["name"] for item in inspector.get_columns("users")}
    if "auth_version" not in user_columns:
        op.add_column(
            "users",
            sa.Column(
                "auth_version",
                sa.Integer(),
                nullable=False,
                server_default="1",
            ),
        )
    if "must_change_password" not in user_columns:
        op.add_column(
            "users",
            sa.Column(
                "must_change_password",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )
        # Nao e possivel saber se senhas antigas atendem a nova politica porque
        # apenas os hashes sao armazenados. Por isso, toda conta existente precisa
        # escolher uma nova senha no primeiro acesso apos a atualizacao.
        op.execute(sa.text("UPDATE users SET must_change_password = true"))

    # Impede contas duplicadas que diferem apenas por letras maiusculas/minusculas,
    # inclusive em duas requisicoes concorrentes.
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_lower "
            "ON users (lower(email))"
        )
    )

    tables = set(inspector.get_table_names())
    if "login_throttles" not in tables:
        op.create_table(
            "login_throttles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("scope", sa.String(length=20), nullable=False),
            sa.Column("key_hash", sa.String(length=64), nullable=False),
            sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("lock_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "scope",
                "key_hash",
                name="uq_login_throttles_scope_key",
            ),
        )
        op.create_index("ix_login_throttles_scope", "login_throttles", ["scope"])
        op.create_index("ix_login_throttles_key_hash", "login_throttles", ["key_hash"])
        op.create_index(
            "ix_login_throttles_locked_until",
            "login_throttles",
            ["locked_until"],
        )

    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "revoked_tokens" not in tables:
        op.create_table(
            "revoked_tokens",
            sa.Column("jti", sa.String(length=64), primary_key=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "revoked_tokens" in tables:
        op.drop_table("revoked_tokens")
    if "login_throttles" in tables:
        op.drop_table("login_throttles")

    op.execute(sa.text("DROP INDEX IF EXISTS uq_users_email_lower"))
    user_columns = {item["name"] for item in inspector.get_columns("users")}
    if "must_change_password" in user_columns:
        op.drop_column("users", "must_change_password")
    if "auth_version" in user_columns:
        op.drop_column("users", "auth_version")
