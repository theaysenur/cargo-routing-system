# admin_routes.py
from flask import Blueprint, jsonify, request
from database.db import get_db_connection
import json

from algorithms.road_graph import shortest_path_coords
from algorithms.vehicle_planner import plan_routes

admin_bp = Blueprint("admin", __name__)

# -------------------------------------------------
# İSİM NORMALİZASYONU
# -------------------------------------------------
def normalize_name(name: str) -> str:
    if not name:
        return ""
    return (
        name.replace("İ", "I")
            .replace("ı", "i")
            .replace("ş", "s")
            .replace("Ş", "S")
            .replace("ğ", "g")
            .replace("Ğ", "G")
            .replace("ç", "c")
            .replace("Ç", "C")
            .replace("ö", "o")
            .replace("Ö", "O")
            .replace("ü", "u")
            .replace("Ü", "U")
            .strip()
    )

# -------------------------------------------------
# DEPOT
# -------------------------------------------------
DEPOT = {
    "name": normalize_name("Umuttepe"),
    "lat": 40.8245,
    "lon": 29.9217,
    "total_weight": 0,
    "cargo_count": 0,
    "station_id": None,
    "cargo_request_id": None
}

# -------------------------------------------------
# MALİYET
# -------------------------------------------------
COST_PER_KM = 1.0

# -------------------------------------------------
# STATIONS
# -------------------------------------------------
@admin_bp.route("/admin/stations", methods=["POST"])
def add_station():
    data = request.get_json()

    name = normalize_name(data.get("name"))
    lat = data.get("lat")
    lon = data.get("lon")

    if not name or lat is None or lon is None:
        return jsonify({"error": "Eksik veri"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO stations (name, lat, lon)
        VALUES (?, ?, ?)
        """,
        (name, lat, lon)
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "İstasyon eklendi"}), 201

@admin_bp.route("/admin/stations", methods=["GET"])
def get_stations():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, lat, lon FROM stations")
    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {"id": r[0], "name": r[1], "lat": r[2], "lon": r[3]}
        for r in rows
    ])

# -------------------------------------------------
# SCENARIOS
# -------------------------------------------------
@admin_bp.route("/admin/scenarios", methods=["GET"])
def get_scenarios():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, scenario_name FROM scenarios ORDER BY id")
    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {"id": r[0], "name": r[1]}
        for r in rows
    ])

# -------------------------------------------------
# ROUTE CALCULATION
# -------------------------------------------------
@admin_bp.route("/admin/route/<int:scenario_id>", methods=["GET"])
def calculate_route(scenario_id):

    mode = request.args.get("mode", "UNLIMITED")
    allow_rental = (mode == "UNLIMITED")

    cargo_mode = request.args.get("cargo_mode", "MAX_WEIGHT")
    if cargo_mode not in ("MAX_WEIGHT", "MAX_COUNT"):
        cargo_mode = "MAX_WEIGHT"

    conn = get_db_connection()
    cursor = conn.cursor()

    # -------------------------------------------------
    # ARAÇLAR
    # -------------------------------------------------
    cursor.execute("SELECT id, capacity, ISNULL(rental_cost, 0) FROM vehicles")
    vehicle_rows = cursor.fetchall()

    FREE_VEHICLE_ID_BY_CAPACITY = {}
    RENTAL_VEHICLE_ID_BY_CAPACITY = {}

    vehicles = []
    rental_vehicle = None

    for vid, cap, rc in vehicle_rows:
        vid = int(vid)
        cap = int(cap)
        rc = float(rc or 0)

        if rc == 0:
            vehicles.append({
                "name": f"V_{vid}",
                "capacity": cap,
                "rental_cost": 0
            })
            FREE_VEHICLE_ID_BY_CAPACITY[cap] = vid
        else:
            RENTAL_VEHICLE_ID_BY_CAPACITY[cap] = vid
            if allow_rental and rental_vehicle is None:
                rental_vehicle = {
                    "capacity": cap,
                    "rental_cost": rc
                }

    if allow_rental and rental_vehicle is None:
        rental_vehicle = {"capacity": 500, "rental_cost": 200}

    if not allow_rental:
        rental_vehicle = None

    # -------------------------------------------------
    # KARGO REQUEST OKUMA
    # -------------------------------------------------
    cursor.execute("""
        SELECT
            c.id AS cargo_request_id,
            s.id AS station_id,
            s.name,
            s.lat,
            s.lon,
            c.total_weight,
            c.cargo_count
        FROM cargo_requests c
        JOIN stations s ON s.id = c.station_id
        WHERE c.scenario_id = ?
        ORDER BY s.id, c.id
    """, (scenario_id,))
    rows = cursor.fetchall()

    stations = []
    for crid, sid, name, lat, lon, w, c in rows:
        w = float(w or 0)
        if w <= 0:
            continue

        stations.append({
            "cargo_request_id": int(crid),
            "station_id": int(sid),
            "name": normalize_name(name),
            "lat": float(lat),
            "lon": float(lon),
            "total_weight": w,
            "cargo_count": int(c or 0)
        })

    if not stations:
        conn.close()
        return jsonify({
            "scenario_id": scenario_id,
            "routes": [],
            "rejected": [],
            "message": "Bu senaryoda kargo bulunamadı."
        })

    # -------------------------------------------------
    # ROTA PLANLAMA (SPLIT DESTEKLİ)
    # -------------------------------------------------
    plans, rejected = plan_routes(
        stations=stations,
        vehicles=vehicles,
        allow_rental=allow_rental,
        rental_vehicle=rental_vehicle,
        cargo_mode=cargo_mode
    )

    if not plans:
        conn.close()
        return jsonify({
            "scenario_id": scenario_id,
            "routes": [],
            "rejected": rejected or []
        })

    # -------------------------------------------------
    # STATUS UPDATE
    # -------------------------------------------------
    if not allow_rental:
        cursor.execute("""
            UPDATE cargo_requests
            SET status = 'REJECTED'
            WHERE scenario_id = ?
        """, (scenario_id,))

        accepted_ids = set()
        for plan in plans:
            for stop in plan["route"]:
                accepted_ids.add(int(stop["cargo_request_id"]))

        for cid in accepted_ids:
            cursor.execute("""
                UPDATE cargo_requests
                SET status = 'ACCEPTED'
                WHERE id = ?
            """, (cid,))
    else:
        cursor.execute("""
            UPDATE cargo_requests
            SET status = 'ACCEPTED'
            WHERE scenario_id = ?
        """, (scenario_id,))
    # -------------------------------------------------
    # 🔥 AYNI SENARYONUN ESKİ ROUTE / TRIP KAYITLARINI TEMİZLE
    # (Her senaryo çalıştırmada tek sonuç mantığı)
    # -------------------------------------------------
    cursor.execute("""
        DELETE FROM trip_stations
        WHERE trip_id IN (SELECT id FROM trips WHERE scenario_id = ?)
    """, (scenario_id,))

    cursor.execute("""
        DELETE FROM trip_cargo
        WHERE trip_id IN (SELECT id FROM trips WHERE scenario_id = ?)
    """, (scenario_id,))

    cursor.execute("""
        DELETE FROM trips
        WHERE scenario_id = ?
    """, (scenario_id,))

    conn.commit()

    # -------------------------------------------------
    # TRIPS + POLYLINE
    # -------------------------------------------------
    response_routes = []
    total_distance_km = 0.0
    total_cost = 0.0

    for plan in plans:
        stops = plan["route"]
        route_names = (
           [DEPOT["name"]] +
             [s["name"] for s in stops] +
             [DEPOT["name"]]
)

        if not stops:
            continue

        full_route = [DEPOT] + stops + [DEPOT]
        full_coords = []
        total_m = 0.0

        for i in range(len(full_route) - 1):
            a = full_route[i]
            b = full_route[i + 1]

            coords, dist_m = shortest_path_coords(
                float(a["lat"]), float(a["lon"]),
                float(b["lat"]), float(b["lon"])
            )

            if not coords:
                continue

            total_m += float(dist_m or 0)
            if full_coords:
                coords = coords[1:]
            full_coords.extend(coords)

        distance_km = total_m / 1000.0
        road_cost = distance_km * COST_PER_KM
        rental_cost = float(plan.get("rental_cost", 0) or 0)
        vehicle_cost = road_cost + rental_cost

        total_distance_km += distance_km
        total_cost += vehicle_cost

        cap = int(plan["capacity"])
        if rental_cost > 0:
            vehicle_id = RENTAL_VEHICLE_ID_BY_CAPACITY.get(cap)
        else:
            vehicle_id = FREE_VEHICLE_ID_BY_CAPACITY.get(cap)

        path_coords = json.dumps(full_coords)  # 🔥 polyline JSON

        cursor.execute("""
    INSERT INTO trips (scenario_id, vehicle_id, total_distance, total_cost, polyline)
    OUTPUT INSERTED.id
    VALUES (?, ?, ?, ?, ?)
         """, (
           scenario_id,
             int(vehicle_id),
             float(distance_km),
              float(vehicle_cost),
             path_coords
))

        trip_id = cursor.fetchone()[0]

        # trip_stations (aynı istasyon 1 kez)
        seen_stations = set()
        visit_order = 1
        for stop in stops:
            sid = stop["station_id"]
            if sid in seen_stations:
                continue
            seen_stations.add(sid)

            cursor.execute("""
                INSERT INTO trip_stations (trip_id, station_id, visit_order)
                VALUES (?, ?, ?)
            """, (trip_id, sid, visit_order))
            visit_order += 1

        # trip_cargo (split destekli – tekrar eklenmez)
        seen_cargo = set()
        for stop in stops:
            cid = int(stop["cargo_request_id"])
            if cid in seen_cargo:
                continue
            seen_cargo.add(cid)

            cursor.execute("""
                INSERT INTO trip_cargo (trip_id, cargo_request_id)
                VALUES (?, ?)
            """, (trip_id, cid))

        response_routes.append({
    "vehicle_id": int(vehicle_id),
    "vehicle_name": plan["vehicle"],
    "capacity": cap,
    "carried_weight": sum(float(s["total_weight"]) for s in stops),
    "distance_km": float(distance_km),
    "road_cost": float(road_cost),
    "rental_cost": float(rental_cost),
    "total_cost": float(vehicle_cost),

    # 🔴 METİNSEL ROTA (FRONTEND BUNU BEKLİYOR)
    "route": route_names,

    # 🗺️ HARİTA ÇİZİMİ İÇİN
    "polyline": full_coords
})

    # -------------------------------------------------
    # REDDEDİLEN KARGO SAYISI
    # -------------------------------------------------
    cursor.execute("""
        SELECT COUNT(*)
        FROM cargo_requests
        WHERE scenario_id = ? AND status = 'REJECTED'
    """, (scenario_id,))
    rejected_count = int(cursor.fetchone()[0] or 0)

    conn.commit()
    conn.close()

    return jsonify({
        "scenario_id": scenario_id,
        "mode": mode,
        "cargo_mode": cargo_mode,
        "vehicle_count": len(response_routes),
        "total_distance_km": float(total_distance_km),
        "total_cost": float(total_cost),
        "routes": response_routes,
        "rejected": rejected or [],
        "rejected_count": rejected_count
    })
# CREATE SCENARIO
# -------------------------------------------------
@admin_bp.route("/admin/scenario", methods=["POST", "OPTIONS"])
def create_scenario():

    # 🔥 PRE-FLIGHT (CORS) İSTEĞİ
    if request.method == "OPTIONS":
        return "", 200

    # 🔥 GERÇEK POST İSTEĞİ
    data = request.get_json()
    scenario_name = data.get("scenario_name")

    if not scenario_name:
        return jsonify({"error": "scenario_name missing"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    user_id = data.get("user_id")

    cursor.execute("""
        INSERT INTO scenarios (scenario_name, scenario_date, user_id)
        OUTPUT INSERTED.id
        VALUES (?, GETDATE(), ?)
    """, (scenario_name, user_id))


    scenario_id = cursor.fetchone()[0]

    conn.commit()
    conn.close()

    return jsonify({
        "id": scenario_id,
        "name": scenario_name
    })

@admin_bp.route("/admin/scenario/<int:scenario_id>/details", methods=["GET"])
def scenario_details(scenario_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Trips (araç rotaları)
    cursor.execute("""
        SELECT t.id, t.vehicle_id, t.total_distance, t.total_cost, t.polyline
        FROM trips t
        WHERE t.scenario_id = ?
        ORDER BY t.id
    """, (scenario_id,))
    trips = cursor.fetchall()

    if not trips:
        conn.close()
        return jsonify({"scenario_id": scenario_id, "trips": [], "totals": {"distance_km": 0, "cost": 0}})

    trips_out = []
    total_cost = 0.0
    total_dist = 0.0

    for trip_id, vehicle_id, dist, cost, polyline in trips:
        total_cost += float(cost or 0)
        total_dist += float(dist or 0)

        # Trip stations -> rota isimleri
        cursor.execute("""
            SELECT s.name
            FROM trip_stations ts
            JOIN stations s ON s.id = ts.station_id
            WHERE ts.trip_id = ?
            ORDER BY ts.visit_order
        """, (trip_id,))
        station_names = [r[0] for r in cursor.fetchall()]
        route_names = ["Umuttepe"] + station_names + ["Umuttepe"]

        # Trip cargo -> hangi kargolar / hangi kullanıcılar
        cursor.execute("""
            SELECT
                cr.id as cargo_request_id,
                cr.user_id,
                u.username,
                s.name as station_name,
                cr.total_weight,
                cr.cargo_count
            FROM trip_cargo tc
            JOIN cargo_requests cr ON cr.id = tc.cargo_request_id
            LEFT JOIN users u ON u.id = cr.user_id
            JOIN stations s ON s.id = cr.station_id
            WHERE tc.trip_id = ?
            ORDER BY cr.id
        """, (trip_id,))
        cargo_rows = cursor.fetchall()

        cargos = []
        user_set = set()
        for cid, uid, uname, stname, w, cnt in cargo_rows:
            user_set.add((int(uid), uname or f"User {uid}"))
            cargos.append({
                "cargo_request_id": int(cid),
                "user_id": int(uid),
                "username": uname or f"User {uid}",
                "station": stname,
                "total_weight": float(w or 0),
                "cargo_count": int(cnt or 0),
            })

        trips_out.append({
            "trip_id": int(trip_id),
            "vehicle_id": int(vehicle_id),
            "distance_km": float(dist or 0),
            "total_cost": float(cost or 0),
            "route": route_names,
            "polyline": json.loads(polyline) if polyline else [],
            "users": [{"user_id": uid, "username": uname} for (uid, uname) in sorted(user_set)],
            "cargos": cargos,
        })

    conn.close()
    return jsonify({
        "scenario_id": int(scenario_id),
        "totals": {"distance_km": float(total_dist), "cost": float(total_cost)},
        "trips": trips_out
    })
@admin_bp.route("/admin/scenarios/summary", methods=["GET"])
def scenarios_summary():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Senaryo bazında: araç sayısı, toplam mesafe, toplam maliyet, reddedilen kargo sayısı, kullanıcı sayısı
    cursor.execute("""
        SELECT
            s.id as scenario_id,
            s.scenario_name,
            COUNT(DISTINCT t.id) as vehicle_count,
            ISNULL(SUM(t.total_distance), 0) as total_distance_km,
            ISNULL(SUM(t.total_cost), 0) as total_cost,
            ISNULL(SUM(CASE WHEN cr.status='REJECTED' THEN 1 ELSE 0 END), 0) as rejected_count,
            COUNT(DISTINCT cr.user_id) as user_count
        FROM scenarios s
        LEFT JOIN trips t ON t.scenario_id = s.id
        LEFT JOIN cargo_requests cr ON cr.scenario_id = s.id
        GROUP BY s.id, s.scenario_name
        ORDER BY s.id
    """)

    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "scenario_id": int(r[0]),
            "scenario_name": r[1],
            "vehicle_count": int(r[2] or 0),
            "total_distance_km": float(r[3] or 0),
            "total_cost": float(r[4] or 0),
            "rejected_count": int(r[5] or 0),
            "user_count": int(r[6] or 0),
        }
        for r in rows
    ])
