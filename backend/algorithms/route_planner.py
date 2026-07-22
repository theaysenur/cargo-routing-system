# route_planner.py
import pickle
import os

# =================================================
# DISTANCE MATRIX YÜKLE
# =================================================
_PATH = os.path.join(os.path.dirname(__file__), "distance_matrix.pkl")
with open(_PATH, "rb") as f:
    DIST_M = pickle.load(f)

# =================================================
# İSİM NORMALİZASYONU (TEK KAYNAK)
# =================================================
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

# =================================================
# DEPOT (TEK VE STANDART)
# =================================================
DEPOT_NAME = normalize_name("Izmit")

# =================================================
# HIZLI MESAFE (KORUMALI)
# =================================================
def fast_distance(a, b):
    """
    Mesafe matrisi üzerinden güvenli mesafe okuma.
    - İsimler normalize edilir
    - Ters yön kontrol edilir
    - Eksikse büyük ceza döner (algoritma çökmez)
    """
    a_n = normalize_name(a)
    b_n = normalize_name(b)

    if a_n in DIST_M and b_n in DIST_M[a_n]:
        return DIST_M[a_n][b_n]

    if b_n in DIST_M and a_n in DIST_M[b_n]:
        return DIST_M[b_n][a_n]

    # 🔴 Kritik ama çökmesin
    print(f"[WARN] Distance missing: {a_n} -> {b_n}")
    return 1e9  # çok büyük mesafe (ceza)

# =================================================
# TEK ARAÇ – NEAREST NEIGHBOR
# =================================================
def plan_one_vehicle_nearest_neighbor(
    remaining,
    capacity,
    cargo_mode="MAX_WEIGHT"
):
    """
    cargo_mode:
      - MAX_WEIGHT : en yakın + ağırlık kısıtı
      - MAX_COUNT  : önce kargo sayısı, eşitse mesafe

    Not: kapasite daima total_weight üzerinden kontrol edilir
    """
    current = DEPOT_NAME
    cap = capacity
    route = []
    rem = remaining[:]

    while True:
        if cargo_mode == "MAX_COUNT":
            candidates = [
                s for s in rem
                if s.get("total_weight", 0) > 0
                and s.get("cargo_count", 0) > 0
                and s.get("total_weight", 0) <= cap
            ]
        else:  # MAX_WEIGHT
            candidates = [
                s for s in rem
                if s.get("total_weight", 0) > 0
                and s.get("total_weight", 0) <= cap
            ]

        if not candidates:
            break

        if cargo_mode == "MAX_COUNT":
            best = min(
                candidates,
                key=lambda s: (
                    -s.get("cargo_count", 0),
                    fast_distance(current, s["name"])
                )
            )
        else:
            best = min(
                candidates,
                key=lambda s: fast_distance(current, s["name"])
            )

        route.append(best)
        cap -= best.get("total_weight", 0)
        rem.remove(best)
        current = best["name"]

    return route, rem

# =================================================
# ÇOK ARAÇLI PLANLAMA
# =================================================
def plan_routes_multi_vehicle(
    stations,
    vehicles,
    allow_rental=False,
    rental_vehicle=None,
    cargo_mode="MAX_WEIGHT"
):
    """
    cargo_mode:
      - MAX_WEIGHT
      - MAX_COUNT
    """
    remaining = stations[:]
    plans = []

    # 🚚 Mevcut araçlar
    for v in vehicles:
        if not remaining:
            break

        route, remaining = plan_one_vehicle_nearest_neighbor(
            remaining,
            v["capacity"],
            cargo_mode=cargo_mode
        )

        if route:
            plans.append({
                "vehicle": v["name"],
                "capacity": v["capacity"],
                "rental_cost": v.get("rental_cost", 0),
                "route": route
            })

    # 🚛 Kiralık araçlar
    if allow_rental and rental_vehicle:
        k = 1
        while remaining:
            route, new_remaining = plan_one_vehicle_nearest_neighbor(
                remaining,
                rental_vehicle["capacity"],
                cargo_mode=cargo_mode
            )

            if not route:
                break

            plans.append({
                "vehicle": f"RENTAL_{k}",
                "capacity": rental_vehicle["capacity"],
                "rental_cost": rental_vehicle["rental_cost"],
                "route": route
            })

            remaining = new_remaining
            k += 1

    return plans, remaining
