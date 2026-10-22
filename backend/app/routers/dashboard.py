from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.delivery import Delivery
from app.models.enums import DeliveryStatus, RouteStatus, UserRole, VehicleStatus
from app.models.route import Route
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.dashboard import DashboardSummary


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> DashboardSummary:

    def count(model, *conditions) -> int:
        return int(db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0)

    invoice_total = db.scalar(
        select(func.coalesce(func.sum(Delivery.invoice_value), 0))
    )
    freight_total = db.scalar(
        select(func.coalesce(func.sum(Delivery.freight_value), 0))
    )

    return DashboardSummary(
        total_deliveries=count(Delivery),
        pending_deliveries=count(
            Delivery,
            Delivery.status.in_(
                [
                    DeliveryStatus.RECEIVED,
                    DeliveryStatus.SEPARATED,
                    DeliveryStatus.INVOICED,
                    DeliveryStatus.PENDING,
                ]
            ),
        ),
        in_route_deliveries=count(Delivery, Delivery.status == DeliveryStatus.IN_ROUTE),
        delivered_deliveries=count(Delivery, Delivery.status == DeliveryStatus.DELIVERED),
        open_routes=count(Route, Route.status == RouteStatus.OPEN),
        in_progress_routes=count(Route, Route.status == RouteStatus.IN_PROGRESS),
        available_vehicles=count(Vehicle, Vehicle.status == VehicleStatus.AVAILABLE),
        active_drivers=count(
            User,
            User.role == UserRole.DRIVER,
            User.is_active.is_(True),
        ),
        invoice_value_total=Decimal(str(invoice_total or 0)),
        freight_value_total=Decimal(str(freight_total or 0)),
    )
