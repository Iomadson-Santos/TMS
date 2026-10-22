from decimal import Decimal

from sqlalchemy import func, select

from app import models  # noqa: F401
from app.core.database import SessionLocal, create_database_tables
from app.core.security import hash_password
from app.models.delivery import Delivery
from app.models.enums import DeliveryStatus, UserRole, VehicleStatus
from app.models.user import User
from app.models.vehicle import Vehicle


USERS = [
    {
        "name": "Administrador TMS",
        "email": "admin@tmsciranda.com.br",
        "password": "Admin123!",
        "role": UserRole.ADMIN,
    },
    {
        "name": "Operador Logistico",
        "email": "operador@tmsciranda.com.br",
        "password": "Operador123!",
        "role": UserRole.OPERATOR,
    },
    {
        "name": "Motorista Demonstracao",
        "email": "motorista@tmsciranda.com.br",
        "password": "Motorista123!",
        "role": UserRole.DRIVER,
    },
]

VEHICLES = [
    {
        "plate": "ABC1D23",
        "brand": "Mercedes-Benz",
        "model": "Atego 1719",
        "year": 2022,
        "capacity_kg": Decimal("9500.00"),
        "capacity_m3": Decimal("42.000"),
        "current_km": 68420,
        "status": VehicleStatus.AVAILABLE,
    },
    {
        "plate": "DEF4G56",
        "brand": "Volkswagen",
        "model": "Delivery 11.180",
        "year": 2023,
        "capacity_kg": Decimal("6500.00"),
        "capacity_m3": Decimal("31.000"),
        "current_km": 41300,
        "status": VehicleStatus.AVAILABLE,
    },
    {
        "plate": "GHI7J89",
        "brand": "Iveco",
        "model": "Daily 35-160",
        "year": 2021,
        "capacity_kg": Decimal("3200.00"),
        "capacity_m3": Decimal("18.000"),
        "current_km": 85210,
        "status": VehicleStatus.MAINTENANCE,
    },
]

DELIVERIES = [
    ("NF-10001", "Livraria Centro", "Rua Boa Vista, 120", "Sao Paulo", "SP", -23.5489, -46.6388, "620.00", "7.20", "18400.00", "890.00"),
    ("NF-10002", "Papelaria Paulista", "Avenida Paulista, 1500", "Sao Paulo", "SP", -23.5614, -46.6559, "430.00", "5.10", "12900.00", "620.00"),
    ("NF-10003", "Colegio Horizonte", "Rua Vergueiro, 2100", "Sao Paulo", "SP", -23.5847, -46.6322, "980.00", "11.40", "26750.00", "1150.00"),
    ("NF-10004", "Distribuidora ABC", "Avenida Portugal, 980", "Santo Andre", "SP", -23.6576, -46.5317, "1250.00", "14.90", "35400.00", "1480.00"),
    ("NF-10005", "Livros do Vale", "Rua Barao de Jaceguai, 450", "Mogi das Cruzes", "SP", -23.5229, -46.1883, "710.00", "8.30", "21700.00", "980.00"),
    ("NF-10006", "Educacional Campinas", "Avenida Andrade Neves, 600", "Campinas", "SP", -22.9045, -47.0608, "1420.00", "16.60", "41800.00", "1890.00"),
    ("NF-10007", "Ponto do Livro", "Rua XV de Novembro, 90", "Jundiai", "SP", -23.1857, -46.8978, "540.00", "6.20", "16300.00", "760.00"),
    ("NF-10008", "Biblioteca Saber", "Avenida Sao Joao, 750", "Sorocaba", "SP", -23.5015, -47.4526, "860.00", "9.80", "24800.00", "1120.00"),
]


def seed() -> None:
    from app.core.config import settings

    if settings.is_production or not settings.demo_seed_enabled:
        raise RuntimeError(
            "A carga de demonstracao esta desativada. Nao execute seed em producao."
        )

    create_database_tables()
    with SessionLocal() as db:
        for item in USERS:
            email = item["email"].lower()
            user = db.scalar(select(User).where(func.lower(User.email) == email))
            if not user:
                db.add(
                    User(
                        name=item["name"],
                        email=email,
                        password_hash=hash_password(item["password"]),
                        role=item["role"],
                        is_active=True,
                        auth_version=1,
                        must_change_password=True,
                    )
                )

        for item in VEHICLES:
            vehicle = db.scalar(select(Vehicle).where(Vehicle.plate == item["plate"]))
            if not vehicle:
                db.add(Vehicle(**item))

        for (
            invoice_number,
            customer_name,
            address,
            city,
            state,
            latitude,
            longitude,
            weight,
            volume,
            invoice_value,
            freight_value,
        ) in DELIVERIES:
            delivery = db.scalar(
                select(Delivery).where(Delivery.invoice_number == invoice_number)
            )
            if not delivery:
                db.add(
                    Delivery(
                        invoice_number=invoice_number,
                        customer_name=customer_name,
                        address=address,
                        city=city,
                        state=state,
                        latitude=latitude,
                        longitude=longitude,
                        weight_kg=Decimal(weight),
                        volume_m3=Decimal(volume),
                        invoice_value=Decimal(invoice_value),
                        freight_value=Decimal(freight_value),
                        status=DeliveryStatus.PENDING,
                    )
                )

        db.commit()

    print("Banco preparado com dados de demonstracao.")
    print("Administrador: admin@tmsciranda.com.br / Admin123!")
    print("Operador: operador@tmsciranda.com.br / Operador123!")
    print("Motorista: motorista@tmsciranda.com.br / Motorista123!")


if __name__ == "__main__":
    seed()
