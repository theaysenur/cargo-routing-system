from algorithms.route_planner import fast_distance
from algorithms.stations import STATIONS

DEPOT_NAME = "İzmit"  # DB ile aynı isimde olsun!

def route_distance_km(stops):
    """
    stops: [station1, station2, ...]  (depo HARİÇ)
    Gerçek yol mesafesi: Depo->...->Depo
    """
    total_m = 0.0
    seq = [{"name": DEPOT_NAME}] + stops + [{"name": DEPOT_NAME}]

    for i in range(len(seq) - 1):
        a = seq[i]["name"]
        b = seq[i + 1]["name"]
        total_m += fast_distance(a, b)

    return total_m / 1000.0


def route_cost(stops, rental_cost=0, cost_per_km=1.0):
    km = route_distance_km(stops)
    road_cost = km * cost_per_km
    total_cost = road_cost + rental_cost
    return {
        "km": km,
        "road_cost": road_cost,
        "rental_cost": rental_cost,
        "total_cost": total_cost
    }
