# user_routes.py
from flask import Blueprint, request, jsonify
from database.db import get_db_connection
import json

user_bp = Blueprint("user", __name__)

# -------------------------------------------------
# KULLANICI KARGO GÖNDERİMİ
#  - PENDING YOK
#  - Varsayılan status = ACCEPTED
# -------------------------------------------------
@user_bp.route("/user/cargo", methods=["POST"])
def create_cargo_request():
    data = request.json or {}

    required = ["user_id", "station_id", "cargo_count", "total_weight", "scenario_id"]
    for r in required:
        if r not in data:
            return jsonify({"error": "Eksik bilgi"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO cargo_requests
        (user_id, station_id, cargo_count, total_weight, scenario_id, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        int(data["user_id"]),
        int(data["station_id"]),
        int(data["cargo_count"]),
        float(data["total_weight"]),
        int(data["scenario_id"]),
        "ACCEPTED"  
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Kargo başarıyla eklendi",
        "status": "ACCEPTED"
    }), 201


# -------------------------------------------------
# KULLANICI KARGO DURUMLARI
# -------------------------------------------------
@user_bp.route("/user/cargo/status/<int:user_id>", methods=["GET"])
def get_user_cargo_status(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.id,
            s.name,
            c.total_weight,
            c.status,
            c.scenario_id
        FROM cargo_requests c
        JOIN stations s ON s.id = c.station_id
        WHERE c.user_id = ?
        ORDER BY c.id DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "cargo_id": r[0],
            "station": r[1],
            "weight": float(r[2]),
            "status": r[3],
            "scenario_id": r[4]
        }
        for r in rows
    ])
# -------------------------------------------------
# KULLANICIYA AİT ROTALARI GETİR
# -------------------------------------------------
# -------------------------------------------------
# SENARYOYA AİT ROTALARI GETİR (USER)
# -------------------------------------------------
@user_bp.route("/user/routes/<int:scenario_id>", methods=["GET"])
def get_user_routes(scenario_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1️⃣ Trip + polyline bilgisi
    cursor.execute("""
    SELECT
        t.id,
        t.total_distance,
        t.total_cost,
        t.polyline
    FROM trips t
    WHERE t.scenario_id = ?
    ORDER BY t.id
""", (scenario_id,))

    trips = cursor.fetchall()
    if not trips:
        conn.close()
        return jsonify([])

    result = []

    for trip_id, distance, cost, path_coords in trips:
        # 2️⃣ İstasyon isimleri
        cursor.execute("""
            SELECT s.name
            FROM trip_stations ts
            JOIN stations s ON s.id = ts.station_id
            WHERE ts.trip_id = ?
            ORDER BY ts.visit_order
        """, (trip_id,))
        stations = [r[0] for r in cursor.fetchall()]

        result.append({
            "trip_id": int(trip_id),
            "vehicle_name": f"Araç {len(result)+1}",
            "distance_km": float(distance),
            "total_cost": float(cost),
            "route": ["Umuttepe"] + stations + ["Umuttepe"],
            "polyline": json.loads(path_coords) if path_coords else []
        })

    conn.close()
    return jsonify(result)


@user_bp.route("/user/scenarios/<int:user_id>", methods=["GET"])
def get_user_scenarios(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, scenario_name
        FROM scenarios
        WHERE user_id = ?
        ORDER BY id
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {"id": r[0], "name": r[1]}
        for r in rows
    ])
