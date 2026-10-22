from math import asin, cos, radians, sin, sqrt

from app.models.delivery import Delivery


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0088
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    )
    return 2 * radius_km * asin(sqrt(a))


def optimize_deliveries(deliveries: list[Delivery]) -> tuple[list[Delivery], float, list[int]]:
    with_coordinates = [
        item
        for item in deliveries
        if item.latitude is not None and item.longitude is not None
    ]
    missing = [item for item in deliveries if item not in with_coordinates]

    if len(with_coordinates) < 2:
        ordered = with_coordinates + missing
        return ordered, 0.0, [item.id for item in missing]

    ordered = [with_coordinates.pop(0)]
    distance = 0.0

    while with_coordinates:
        current = ordered[-1]
        nearest = min(
            with_coordinates,
            key=lambda candidate: haversine_km(
                float(current.latitude),
                float(current.longitude),
                float(candidate.latitude),
                float(candidate.longitude),
            ),
        )
        distance += haversine_km(
            float(current.latitude),
            float(current.longitude),
            float(nearest.latitude),
            float(nearest.longitude),
        )
        ordered.append(nearest)
        with_coordinates.remove(nearest)

    ordered.extend(missing)
    return ordered, round(distance, 2), [item.id for item in missing]
