import folium
import os
from algorithms.road_graph import shortest_path_coords

DEPOT = {"name": "İzmit", "lat": 40.7667, "lon": 29.9167}

def create_map(plans, filename="routes_map.html"):
    m = folium.Map(location=[40.76, 29.92], zoom_start=10, tiles="OpenStreetMap")
    colors = ["red", "blue", "green", "purple", "orange", "black"]

    for i, p in enumerate(plans):
        color = colors[i % len(colors)]
        stops = p["route"]

        # depo dahil sıra
        seq = [DEPOT] + stops + [DEPOT]

        full_coords = []
        for j in range(len(seq) - 1):
            a = seq[j]
            b = seq[j+1]

            coords, _dist_m = shortest_path_coords(a["lat"], a["lon"], b["lat"], b["lon"])
            if not coords:
                continue
            if full_coords:
                coords = coords[1:]
            full_coords.extend(coords)

        if len(full_coords) >= 2:
            folium.PolyLine(full_coords, color=color, weight=5, opacity=0.8,
                            tooltip=f"Araç {p['vehicle']}").add_to(m)

        for s in seq:
            folium.Marker(
                location=(s["lat"], s["lon"]),
                popup=f"{s['name']} ({p['vehicle']})",
                icon=folium.Icon(color=color)
            ).add_to(m)

    m.save(filename)
    print("Harita oluşturuldu:", os.path.abspath(filename))
