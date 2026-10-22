from enum import Enum


class UserRole(str, Enum):
    ADMIN = "administrador"
    OPERATOR = "operador"
    DRIVER = "motorista"


class VehicleStatus(str, Enum):
    AVAILABLE = "disponivel"
    IN_ROUTE = "em_rota"
    MAINTENANCE = "manutencao"
    INACTIVE = "inativo"


class DeliveryStatus(str, Enum):
    RECEIVED = "recebida"
    SEPARATED = "separada"
    INVOICED = "faturada"
    PENDING = "pendente"
    IN_ROUTE = "em_rota"
    DELIVERED = "entregue"
    RETURNED = "devolvida"
    CANCELED = "cancelada"


class RouteStatus(str, Enum):
    OPEN = "aberta"
    IN_PROGRESS = "em_andamento"
    COMPLETED = "concluida"
    CANCELED = "cancelada"
