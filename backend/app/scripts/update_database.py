from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.database import engine


BACKEND_DIR = Path(__file__).resolve().parents[2]
CORE_TABLES = {"users", "vehicles", "routes", "deliveries", "audit_logs"}


def update_database() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))

    tables = set(inspect(engine).get_table_names())
    if CORE_TABLES.issubset(tables) and "alembic_version" not in tables:
        # Instalacoes antigas podiam ter sido criadas por SQLAlchemy create_all.
        # Marca a estrutura inicial para aplicar somente as atualizacoes seguintes.
        command.stamp(config, "0001_initial")

    command.upgrade(config, "head")
    print("Banco de dados atualizado para a versao mais recente.")


if __name__ == "__main__":
    update_database()
