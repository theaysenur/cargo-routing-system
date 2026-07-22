from flask import Blueprint, jsonify
from database.db import get_db_connection

user_bp = Blueprint("user", __name__)

@user_bp.route("/user/routes/<int:scenario_id>", methods=["GET"])
def get_user_routes(scenario_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            t.id AS trip_id,
            t.total_distance,
            t.total_cost,
            s.name,
            ts.visit_order
        FROM trips t
        JOIN trip_stations ts ON ts.trip_id = t.id
        JOIN stations s ON s.id = ts.station_id
        WHERE t.scenario_id = ?
        ORDER BY t.id, ts.visit_order
    """, (scenario_id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify([])

    routes = {}

    for trip_id, distance, cost, station_name, _ in rows:
        if trip_id not in routes:
            routes[trip_id] = {
                "distance_km": float(distance),
                "total_cost": float(cost),
                "route": []
            }

        routes[trip_id]["route"].append(station_name)

    return jsonify(list(routes.values()))
