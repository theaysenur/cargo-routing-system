def save_trip(
    conn,
    scenario_id,
    vehicle_id,
    distance_km,
    total_cost,
    stations
):
    cursor = conn.cursor()

    # 1️⃣ trips
    cursor.execute("""
        INSERT INTO trips (scenario_id, vehicle_id, total_distance, total_cost)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?)
    """, (
        scenario_id,
        vehicle_id,
        distance_km,
        total_cost
    ))

    trip_id = cursor.fetchone()[0]

    # 2️⃣ trip_stations
    order = 1
    for s in stations:
        cursor.execute("""
            INSERT INTO trip_stations (trip_id, station_id, visit_order)
            VALUES (?, ?, ?)
        """, (
            trip_id,
            s["station_id"],
            order
        ))
        order += 1

    conn.commit()
    return trip_id
