#!/usr/bin/env python3
"""
Test Senaryo 3 için kargo dağılımı
"""

from vehicle_planner import plan_routes

# Senaryo 3 verileri (PDF'den)
test_stations = [
    {"name": "Çayırova", "total_weight": 700, "cargo_count": 3},
    {"name": "Dilovası", "total_weight": 800, "cargo_count": 4},
    {"name": "Gebze", "total_weight": 900, "cargo_count": 5},
    {"name": "İzmit", "total_weight": 300, "cargo_count": 5},
]

print("=== SENARYO 3 TESTİ ===")
print(f"Toplam istasyon: {len(test_stations)}")
total_weight = sum(s["total_weight"] for s in test_stations)
print(f"Toplam ağırlık: {total_weight} kg")
print(f"Toplam kargo adedi: {sum(s['cargo_count'] for s in test_stations)}")

print("\n--- UNLIMITED MOD (Sınırsız Araç) ---")
plans, remaining = plan_routes(
    test_stations, 
    allow_rental=True, 
    cargo_mode="MAX_WEIGHT"
)

print(f"Oluşturulan rota sayısı: {len(plans)}")
print(f"Reddedilen kargo: {len(remaining)}")

rental_count = sum(1 for p in plans if 'RENTAL' in p['vehicle'])
print(f"Kiralık araç sayısı: {rental_count}")

print("\n--- Araç Detayları ---")
for i, p in enumerate(plans):
    used_weight = sum(st["total_weight"] for st in p["route"])
    station_names = [st["name"] for st in p["route"]]
    print(f"{i+1}. {p['vehicle']}: {used_weight:.0f}kg / {p['capacity']:.0f}kg")
    print(f"   İstasyonlar: {', '.join(station_names)}")
    if p.get('rental_cost', 0) > 0:
        print(f"   Kiralama maliyeti: {p['rental_cost']} birim")

print("\n--- LIMITED MOD (Belirli Sayıda Araç) ---")
plans_limited, rejected = plan_routes(
    test_stations, 
    allow_rental=False, 
    cargo_mode="MAX_WEIGHT"
)

print(f"Oluşturulan rota sayısı: {len(plans_limited)}")
print(f"Reddedilen kargo: {len(rejected)}")
if rejected:
    print(f"Reddedilen istasyonlar: {[r['name'] for r in rejected]}")