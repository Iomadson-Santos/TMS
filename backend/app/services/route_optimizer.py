import math

from app.schemas.route import StopCreate


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    value = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return radius_km * 2 * math.asin(math.sqrt(value))


def nearest_neighbor(origem_lat: float, origem_lng: float, paradas: list[StopCreate]) -> list[StopCreate]:
    restantes = list(paradas)
    ordem: list[StopCreate] = []
    lat, lng = origem_lat, origem_lng
    while restantes:
        proxima = min(restantes, key=lambda p: haversine(lat, lng, p.lat, p.lng))
        restantes.remove(proxima)
        ordem.append(proxima)
        lat, lng = proxima.lat, proxima.lng
    return ordem


def calcular_distancia_total(origem_lat: float, origem_lng: float, paradas: list[StopCreate]) -> float:
    distancia = 0.0
    lat, lng = origem_lat, origem_lng
    for parada in paradas:
        distancia += haversine(lat, lng, parada.lat, parada.lng)
        lat, lng = parada.lat, parada.lng
    return round(distancia, 2)
