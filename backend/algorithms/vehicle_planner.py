from __future__ import annotations

import math
from typing import Dict, List, Tuple, Optional

from algorithms.route_planner import fast_distance, DEPOT_NAME
from algorithms.route_costs import route_cost

# -----------------------------
# Default vehicle set (PDF)
# -----------------------------
BASE_VEHICLES = [
    {"name": "V1", "capacity": 1000, "rental_cost": 0},
    {"name": "V2", "capacity": 750,  "rental_cost": 0},
    {"name": "V3", "capacity": 500,  "rental_cost": 0},
]

RENTAL_VEHICLE = {"capacity": 500, "rental_cost": 200}

# -----------------------------
# Helpers
# -----------------------------
def _km(a_name: str, b_name: str) -> float:
    """Road distance in km based on the precomputed matrix (GraphML)."""
    return fast_distance(a_name, b_name) / 1000.0


def _station_value(st: Dict, cargo_mode: str) -> float:
    """LIMITED objective value (MAX_COUNT or MAX_WEIGHT)."""
    if cargo_mode == "MAX_COUNT":
        return float(st.get("cargo_count", 0) or 0)
    return float(st.get("total_weight", 0) or 0)


def _station_weight(st: Dict) -> float:
    return float(st.get("total_weight", 0) or 0)


def _density(st: Dict, cargo_mode: str) -> float:
    """
    Value-per-km heuristic (LIMITED only).
    Yakın ve (ağır / çok adet) olan istasyonlar öncelikli olur.
    """
    d = _km(DEPOT_NAME, st["name"])
    v = _station_value(st, cargo_mode)
    return v / max(d, 0.1)


def _total_capacity(vehicles: List[Dict]) -> float:
    return float(sum(float(v["capacity"]) for v in vehicles))


def _clean_stations(stations: List[Dict]) -> List[Dict]:
    """Drop zero cargos; normalize missing fields."""
    out = []
    for s in stations:
        if s.get("name") is None:
            continue
        w = float(s.get("total_weight", 0) or 0)
        c = int(s.get("cargo_count", 0) or 0)
        if w <= 0:
            continue
        s2 = dict(s)
        s2["total_weight"] = float(w)
        s2["cargo_count"] = int(c)
        out.append(s2)
    return out


def _assert_capacity(route: List[Dict], capacity: float, vehicle_name: str) -> None:
    """Hard guard: never allow capacity violation."""
    total_w = sum(_station_weight(x) for x in route)
    if total_w - capacity > 1e-9:
        raise ValueError(
            f"Capacity violation on {vehicle_name}: total={total_w} > cap={capacity}"
        )
def _route_total_cost(route: List[Dict], cost_per_km: float, rental_cost: float) -> float:
    """
    Toplam rota maliyeti (GLOBAL):
    yol maliyeti + varsa kiralama maliyeti
    """
    result = route_cost(
        route,
        cost_per_km=cost_per_km,
        rental_cost=rental_cost,
    )
    return float(result.get("total_cost", 0.0))
def _insert_best(route: List[Dict], st: Dict) -> List[Dict]:
    return route + [st]



# -----------------------------
# SPLIT DELIVERY (UNLIMITED only)
# -----------------------------
def _split_stations_for_capacity(stations: List[Dict], max_piece: float) -> List[Dict]:
    """
    Split each station's total_weight into chunks <= max_piece.
    Keeps cargo_request_id and station_id for DB linking.

    Example: 900 -> 500 + 400
    """
    out: List[Dict] = []
    for st in stations:
        w = float(st.get("total_weight", 0) or 0)
        if w <= 0:
            continue

        remaining = w
        part_idx = 1
        while remaining > 1e-9:
            take = min(max_piece, remaining)
            s2 = dict(st)
            s2["total_weight"] = float(take)
            s2["cargo_part_index"] = part_idx
            s2["is_split_part"] = True
            out.append(s2)
            remaining -= take
            part_idx += 1
    return out

# -----------------------------
# LIMITED: choose accepted cargos (may reject)
# -----------------------------
def _pick_subset_limited(
    stations: List[Dict],
    vehicles: List[Dict],
    cargo_mode: str,
) -> Tuple[List[Dict], List[Dict]]:

    capacity = _total_capacity(vehicles)

    # -----------------------------
    # SIRALAMA KRİTERİ
    # -----------------------------
    if cargo_mode == "MAX_WEIGHT":
        # Ağır olanlar önce
        ordered = sorted(
            stations,
            key=lambda s: (
                _station_weight(s),              # ağırlık
                _density(s, "MAX_WEIGHT"),       # yakınlık bonus
            ),
            reverse=True,
        )
    else:  # MAX_COUNT
        # Hafif ve çok kargo olanlar önce
        ordered = sorted(
            stations,
            key=lambda s: (
                s.get("cargo_count", 1),         # adet
                -_station_weight(s),              # hafiflik
            ),
            reverse=True,
        )

    accepted: List[Dict] = []
    remaining = capacity

    for s in ordered:
        w = _station_weight(s)
        if w <= remaining:
            accepted.append(s)
            remaining -= w

    rejected = [s for s in stations if s not in accepted]
    return accepted, rejected

# -----------------------------
# LIMITED: assignment (capacity-safe)
# -----------------------------
def _assign_limited_capacity_safe(
    stations: List[Dict],
    vehicles: List[Dict],
    cargo_mode: str,
) -> Tuple[List[Dict], List[Dict]]:

    if cargo_mode == "MAX_COUNT":
        # Önce çok adet, sonra hafiflik, sonra yakınlık/yoğunluk
        ordered = sorted(
            stations,
            key=lambda s: (
                int(s.get("cargo_count", 0) or 0),   # adet büyük
                -_station_weight(s),                 # hafif olan öne (reverse=True ile)
                _density(s, "MAX_COUNT"),            # yakınlık bonus
            ),
            reverse=True,
        )
    else:  # MAX_WEIGHT
        ordered = sorted(
            stations,
            key=lambda s: (
                _station_weight(s),                  # ağırlık büyük
                _density(s, "MAX_WEIGHT"),           # yakınlık bonus
            ),
            reverse=True,
        )

    plans: List[Dict] = [
        {"vehicle": v["name"], "capacity": float(v["capacity"]),
         "rental_cost": float(v.get("rental_cost", 0) or 0), "route": []}
        for v in vehicles
    ]

    leftover: List[Dict] = []

    for st in ordered:
        w = _station_weight(st)

        candidates = []
        for p in plans:
            used = sum(_station_weight(x) for x in p["route"])
            if used + w <= p["capacity"]:
                # kümelenme skoru: depoya/rotaya yakınlık
                score = _km(DEPOT_NAME, st["name"]) if not p["route"] else min(
                    _km(x["name"], st["name"]) for x in p["route"]
                )
                candidates.append((score, p))

        if not candidates:
            leftover.append(st)
            continue

        candidates.sort(key=lambda t: t[0])
        candidates[0][1]["route"].append(st)

    for p in plans:
        _assert_capacity(p["route"], p["capacity"], p["vehicle"])

    return plans, leftover

# -----------------------------
# UNLIMITED: insertion delta (cheapest insertion)
# -----------------------------
def _insertion_delta_km(route: List[Dict], st_name: str) -> float:
    """
    Cheapest insertion delta (km):
    Δ = d(a,st)+d(st,b)-d(a,b) for best edge (a,b) in current tour.
    Tour assumed: DEPOT -> route[0] -> ... -> route[-1] -> DEPOT
    """
    if not route:
        return 2.0 * _km(DEPOT_NAME, st_name)

    best = float("inf")

    # edge: DEPOT -> first
    first = route[0]["name"]
    best = min(
        best,
        _km(DEPOT_NAME, st_name) + _km(st_name, first) - _km(DEPOT_NAME, first),
    )

    # edges: mid
    for i in range(len(route) - 1):
        a = route[i]["name"]
        b = route[i + 1]["name"]
        best = min(best, _km(a, st_name) + _km(st_name, b) - _km(a, b))

    # edge: last -> DEPOT
    last = route[-1]["name"]
    best = min(
        best,
        _km(last, st_name) + _km(st_name, DEPOT_NAME) - _km(last, DEPOT_NAME),
    )

    return max(best, 0.0)

# -----------------------------
# UNLIMITED: decide place vs rent
# -----------------------------
def _unlimited_place_or_rent(
    st: Dict,
    plans: List[Dict],
    rental_vehicle: Dict,
    cost_per_km: float,
) -> Tuple[str, Optional[Dict], Optional[List[Dict]]]:
    """
    Karar mantığı (DOĞRU HALİ):

    1) Mevcut araçlara eklemenin GERÇEK delta maliyetini hesapla
       - Mandatory rental ise: kiralama maliyeti TEKRAR eklenmez
    2) Yeni kiralık açmanın maliyetini hesapla
    3) Hangisi ucuzsa onu seç

    Dönüş:
      ("EXISTING", plan, new_route)
      ("NEW_RENTAL", None, None)
    """

    w = _station_weight(st)
    rent_cap = float(rental_vehicle["capacity"])

    best_plan: Optional[Dict] = None
    best_new_route: Optional[List[Dict]] = None
    best_delta = float("inf")

    # -------------------------------------------------
    # 1) EXISTING araçlara ekleme denemeleri
    # -------------------------------------------------
    for p in plans:
        used = sum(_station_weight(x) for x in p["route"])
        if used + w > float(p["capacity"]):
            continue

        # 🔥 KRİTİK NOKTA
        # Mandatory rental ise rental_cost = 0 kabul edilir
        rental_cost = float(p.get("rental_cost", 0) or 0)
        #if str(p.get("vehicle", "")).startswith("RENTAL_MAND_"):
           # rental_cost = 0.0

        base_cost = _route_total_cost(
            p["route"],
            cost_per_km,
            rental_cost,
        )

        new_route = p["route"] + [st]

        new_cost = _route_total_cost(
            new_route,
            cost_per_km,
            rental_cost,
        )

        delta = new_cost - base_cost

        if delta < best_delta:
            best_delta = delta
            best_plan = p
            best_new_route = new_route

    # -------------------------------------------------
    # 2) NEW RENTAL seçeneği (sığıyorsa)
    # -------------------------------------------------
    if w <= rent_cap + 1e-9:
        rent_cost = _route_total_cost(
            [st],
            cost_per_km,
            float(rental_vehicle.get("rental_cost", 0) or 0),
        )
    else:
        rent_cost = float("inf")  # sığmıyorsa kiralama opsiyon değil

    # -------------------------------------------------
    # 3) KARAR
    # -------------------------------------------------
    if best_plan is not None and best_delta <= rent_cost + 1e-9:
        return "EXISTING", best_plan, best_new_route

    return "NEW_RENTAL", None, None


# -----------------------------
# UNLIMITED: assignment loop (supports mandatory rentals)
# -----------------------------
def _unlimited_min_cost_assign(
    split_stations: List[Dict],
    free_vehicles: List[Dict],
    rental_vehicle: Dict,
    cost_per_km: float,
    mandatory_rentals: int = 0,
) -> Tuple[List[Dict], List[Dict]]:

    plans: List[Dict] = [
        {
            "vehicle": v["name"],
            "capacity": float(v["capacity"]),
            "rental_cost": float(v.get("rental_cost", 0) or 0),
            "route": [],
        }
        for v in free_vehicles
    ]

    # zorunlu kiralıklar
    for i in range(int(mandatory_rentals)):
        plans.append(
            {
                "vehicle": f"RENTAL_MAND_{i+1}",
                "capacity": float(rental_vehicle["capacity"]),
                "rental_cost": float(rental_vehicle.get("rental_cost", 0) or 0),
                "route": [],
            }
        )

    impossible: List[Dict] = []
    rental_id = 1

    # 🔥 Kritik: UNLIMITED’de “tek parça taşınabilir mi?” kontrolü
    max_single_cap = max(float(p["capacity"]) for p in plans) if plans else 0.0

    ordered = sorted(split_stations, key=lambda s: _station_weight(s), reverse=True)

    for st in ordered:
        w = _station_weight(st)
        if w <= 0:
            continue

        # 🔥 Burada rental cap’e bakmak YANLIŞTI. max_single_cap’e bakıyoruz.
        if w > max_single_cap + 1e-9:
            impossible.append(st)
            continue

        decision, chosen, new_route = _unlimited_place_or_rent(
            st, plans, rental_vehicle, cost_per_km
        )

        if decision == "EXISTING" and chosen is not None and new_route is not None:
            chosen["route"] = new_route
            continue
        if decision == "NEW_RENTAL":
            # ✅ önce boş mandatory kiralık var mı bak
            mand = next(
                (p for p in plans
                if str(p.get("vehicle", "")).startswith("RENTAL_MAND_")
                and not p.get("route")
                and _station_weight(st) <= float(p["capacity"]) + 1e-9),
                None
            )

            if mand is not None:
                mand["route"] = [st]
                continue


        # NEW_RENTAL ancak sığıyorsa açılabilir (place_or_rent zaten inf yapıyor)
        if w <= float(rental_vehicle["capacity"]) + 1e-9:
            plans.append(
                {
                    "vehicle": f"RENTAL_{rental_id}",
                    "capacity": float(rental_vehicle["capacity"]),
                    "rental_cost": float(rental_vehicle.get("rental_cost", 0) or 0),
                    "route": [st],
                }
            )
            rental_id += 1
        else:
            # kiralığa sığmıyor ama free araca sığıyor olmalıydı:
            # bu noktaya geliyorsa, mevcut araçlara yerleştirme başarısız oldu.
            # safe fallback: en büyük kapasiteli uygun araca zorla koy
            placed = False
            for p in sorted(plans, key=lambda x: x["capacity"], reverse=True):
                used = sum(_station_weight(x) for x in p["route"])
                if used + w <= p["capacity"] + 1e-9:
                    p["route"].append(st)
                    placed = True
                    break
            if not placed:
                impossible.append(st)

    for p in plans:
        _assert_capacity(p["route"], p["capacity"], p["vehicle"])
    print("MAND ROUTES:", [(p["vehicle"], len(p["route"])) for p in plans if "RENTAL_MAND" in p["vehicle"]])


    return plans, impossible


# -----------------------------
# Routing order
# -----------------------------
def _nearest_neighbor_order(stops: List[Dict]) -> List[Dict]:
    if not stops:
        return []
    remaining = stops[:]
    current = DEPOT_NAME
    ordered: List[Dict] = []
    while remaining:
        nxt = min(remaining, key=lambda s: _km(current, s["name"]))
        ordered.append(nxt)
        remaining.remove(nxt)
        current = nxt["name"]
    return ordered


def _finalize_routes(plans: List[Dict]) -> List[Dict]:
    out: List[Dict] = []
    for p in plans:
        route = p.get("route", [])
        vname = str(p.get("vehicle", ""))

        # ✅ Mandatory boş bile olsa kalsın
        if not route and vname.startswith("RENTAL_MAND_"):
            out.append(dict(p))
            continue

        if not route:
            continue

        ordered = _nearest_neighbor_order(route)
        _assert_capacity(ordered, p["capacity"], p["vehicle"])
        p2 = dict(p)
        p2["route"] = ordered
        out.append(p2)

    return out



def _try_reduce_rentals(plans: List[Dict]) -> List[Dict]:
    cleaned: List[Dict] = []
    for p in plans:
        vname = str(p.get("vehicle", ""))

        # ✅ Mandatory ASLA silinmez
        if vname.startswith("RENTAL_MAND_"):
            cleaned.append(p)
            continue

        # ✅ Normal rental boşsa sil
        if vname.startswith("RENTAL_") and not p.get("route"):
            continue

        cleaned.append(p)

    return cleaned

# -----------------------------
# Public API
# -----------------------------
# -----------------------------
# Public API
# -----------------------------
def plan_routes(
    
    stations: List[Dict],
    allow_rental: bool = True,          # True -> UNLIMITED, False -> LIMITED
    cargo_mode: str = "MAX_WEIGHT",     # LIMITED only
    cost_per_km: float = 1.0,
    optimize_rentals: bool = True,
    vehicles: Optional[List[Dict]] = None,
    rental_vehicle: Optional[Dict] = None,
) -> Tuple[List[Dict], List[Dict]]:
    print("===== DEBUG PLAN_ROUTES INPUT =====")
    for s in stations:
        print(
            "STATION:",
            s.get("id"),
            s.get("name"),
            "weight=", s.get("total_weight"),
            "scenario=", s.get("scenario_id"),
         )

    print(
        "TOTAL_DEMAND_IN_PLAN_ROUTES =",
        sum(float(s.get("total_weight", 0) or 0) for s in stations)
    )
    print("===================================")
    # -----------------------------
    # Defaults
    # -----------------------------
    if vehicles is None:
        vehicles = [dict(v) for v in BASE_VEHICLES]
    if rental_vehicle is None:
        rental_vehicle = dict(RENTAL_VEHICLE)

    stations = _clean_stations(stations)
    if not stations:
        return [], []

    # -----------------------------
    # Capacity bounds
    # -----------------------------
    max_free_cap = max(float(v["capacity"]) for v in vehicles) if vehicles else 0.0

    # =========================================================
    # LIMITED (no rental, no split)
    # =========================================================
    if not allow_rental:
        too_big = [s for s in stations if _station_weight(s) > max_free_cap]
        feasible = [s for s in stations if _station_weight(s) <= max_free_cap]

        accepted, rejected_by_capacity = _pick_subset_limited(feasible, vehicles, cargo_mode)

        plans, leftover = _assign_limited_capacity_safe(accepted, vehicles, cargo_mode)
        plans = _finalize_routes(plans)

        rejected = too_big + rejected_by_capacity + leftover

        for p in plans:
            p["used_weight"] = sum(_station_weight(st) for st in p["route"])
            p["route_names"] = [DEPOT_NAME] + [st["name"] for st in p["route"]] + [DEPOT_NAME]
            p["cost_breakdown"] = route_cost(
                p["route"],
                cost_per_km=cost_per_km,
                rental_cost=0,
            )
            _assert_capacity(p["route"], p["capacity"], p["vehicle"])

        return plans, rejected

    # =========================================================
    # UNLIMITED (minimum total cost)
    # =========================================================
    # rental_vehicle yoksa unlimited fiilen mümkün değil -> free-only çöz
    if rental_vehicle is None:
        too_big = [s for s in stations if _station_weight(s) > max_free_cap]
        feasible = [s for s in stations if _station_weight(s) <= max_free_cap]

        plans, leftover = _assign_limited_capacity_safe(feasible, vehicles, cargo_mode="MAX_WEIGHT")
        plans = _finalize_routes(plans)

        rejected = too_big + leftover

        for p in plans:
            p["used_weight"] = sum(_station_weight(st) for st in p["route"])
            p["route_names"] = [DEPOT_NAME] + [st["name"] for st in p["route"]] + [DEPOT_NAME]
            p["cost_breakdown"] = route_cost(
                p["route"],
                cost_per_km=cost_per_km,
                rental_cost=0,
            )
            _assert_capacity(p["route"], p["capacity"], p["vehicle"])

        return plans, rejected

    # UNLIMITED: her istasyon split ile taşınabilir sayılır
    feasible = stations[:]
    too_big: List[Dict] = []

    total_demand = sum(_station_weight(s) for s in feasible)
    free_capacity = _total_capacity(vehicles)
    rent_cap = float(rental_vehicle["capacity"])

    # ---------------------------------------------------------
    # 0) Free-only (baseline) çözümü üret (rejectsiz taşıyabiliyorsa)
    #    -> UNLIMITED daha pahalı çıkarsa buna geri döneceğiz
    # ---------------------------------------------------------
    baseline_plans: List[Dict] = []
    baseline_rejected: List[Dict] = []
    baseline_total_cost = float("inf")

    # Baseline sadece şu durumda “tam karşılaştırılabilir”:
    # - toplam kapasite yetiyor
    # - hiçbir istasyon tek araç limiti aşmıyor (split gerekmez)
    baseline_possible = (
        total_demand <= free_capacity + 1e-9
        and all(_station_weight(s) <= max_free_cap + 1e-9 for s in feasible)
    )

    if baseline_possible:
        baseline_plans, baseline_leftover = _assign_limited_capacity_safe(
            feasible, vehicles, cargo_mode="MAX_WEIGHT"
        )
        baseline_plans = _finalize_routes(baseline_plans)
        baseline_rejected = baseline_leftover  # normalde boş olmalı

        for p in baseline_plans:
            p["used_weight"] = sum(_station_weight(st) for st in p["route"])
            p["route_names"] = [DEPOT_NAME] + [st["name"] for st in p["route"]] + [DEPOT_NAME]
            p["cost_breakdown"] = route_cost(
                p["route"],
                cost_per_km=cost_per_km,
                rental_cost=0,
            )
            _assert_capacity(p["route"], p["capacity"], p["vehicle"])

        baseline_total_cost = sum(
            float(p["cost_breakdown"].get("total_cost", 0.0)) for p in baseline_plans
        )

    # ---------------------------------------------------------
    # 1) Mandatory rentals (sadece kapasite yetmiyorsa)
    # ---------------------------------------------------------
    mandatory_rentals = 0
    if total_demand > free_capacity + 1e-9:
        mandatory_rentals = int(math.ceil((total_demand - free_capacity) / rent_cap))

    # ---------------------------------------------------------
    # 2) Split (SADECE gerekiyorsa):
    #    - Bir istasyon max_free_cap’i aşıyorsa split et (UNLIMITED’de)
    #    - Aşmıyorsa split etme
    # ---------------------------------------------------------
    split_all: List[Dict] = []

    for s in feasible:
        w = _station_weight(s)

        if mandatory_rentals > 0:
        
            if w > rent_cap + 1e-9:
                split_all.extend(
                    _split_stations_for_capacity([s], max_piece=rent_cap)
                )
            else:
                split_all.append(s)
        else:
        
            if w > max_free_cap + 1e-9:
                split_all.extend(
                    _split_stations_for_capacity([s], max_piece=rent_cap)
                )
            else:
                split_all.append(s)

    # ---------------------------------------------------------
    # 3) Min-cost assignment (rental sadece daha ucuzsa açılmalı)
    # ---------------------------------------------------------
    plans, impossible = _unlimited_min_cost_assign(
        split_stations=split_all,
        free_vehicles=vehicles,
        rental_vehicle=rental_vehicle,
        cost_per_km=cost_per_km,
        mandatory_rentals=mandatory_rentals,
    )

    plans = _finalize_routes(plans)

    if optimize_rentals:
        plans = _try_reduce_rentals(plans)

    # ---------------------------------------------------------
    # 4) Cost & meta
    # ---------------------------------------------------------
    for p in plans:
        p["used_weight"] = sum(_station_weight(st) for st in p["route"])
        p["route_names"] = [DEPOT_NAME] + [st["name"] for st in p["route"]] + [DEPOT_NAME]
        p["cost_breakdown"] = route_cost(
            p["route"],
            cost_per_km=cost_per_km,
            rental_cost=p.get("rental_cost", 0),
        )
        _assert_capacity(p["route"], p["capacity"], p["vehicle"])

    rejected = too_big + impossible

    unlimited_total_cost = sum(
        float(p["cost_breakdown"].get("total_cost", 0.0)) for p in plans
    )

    # ---------------------------------------------------------
    # 5) Güvenlik freni:
    #    Baseline mümkünse ve UNLIMITED daha pahalıysa -> baseline döndür
    # ---------------------------------------------------------
    if baseline_possible and baseline_rejected == []:
        if unlimited_total_cost > baseline_total_cost + 1e-9:
            return baseline_plans, baseline_rejected

    print(
        f"DEBUG_UNLIMITED: demand={total_demand} "
        f"free_cap={free_capacity} "
        f"mandatory_rentals={mandatory_rentals} "
        f"vehicles={len(plans)} "
        f"rentals={sum(1 for p in plans if 'RENTAL' in str(p['vehicle']))} "
        f"unlim_cost={unlimited_total_cost:.2f} "
        f"base_ok={baseline_possible} base_cost={baseline_total_cost:.2f}"
    )

    return plans, rejected



