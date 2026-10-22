from decimal import Decimal

from app.schemas.base import ORMModel


class DashboardSummary(ORMModel):
    total_deliveries: int
    pending_deliveries: int
    in_route_deliveries: int
    delivered_deliveries: int
    open_routes: int
    in_progress_routes: int
    available_vehicles: int
    active_drivers: int
    invoice_value_total: Decimal
    freight_value_total: Decimal
