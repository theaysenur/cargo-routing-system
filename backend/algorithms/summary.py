from algorithms.route_costs import route_cost

def build_summary(plans):
    """
    plans: plan_with_vehicles çıktısı
    """
    summary = []
    total_cost = 0

    for p in plans:
        cost = route_cost(p["route"], p["rental_cost"])

        carried_weight = sum(
            s.get("total_weight", 0) for s in p["route"]
        )

        row = {
            "vehicle": p["vehicle"],
            "capacity": p["capacity"],
            "carried_weight": carried_weight,
            "km": round(cost["km"], 2),
            "road_cost": round(cost["road_cost"], 2),
            "rental_cost": cost["rental_cost"],
            "total_cost": round(cost["total_cost"], 2),
        }

        total_cost += cost["total_cost"]
        summary.append(row)

    return summary, round(total_cost, 2)
