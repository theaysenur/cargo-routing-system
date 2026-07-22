#road_graph.py
import os
import osmnx as ox
import networkx as nx
from functools import lru_cache

# -------------------------------------------------
# AYARLAR
# -------------------------------------------------
GRAPH_FILE = "kocaeli.graphml"
PLACE_NAME = "Kocaeli, Turkey"

# -------------------------------------------------
# GRAPH CACHE (DISK + RAM)
# -------------------------------------------------
@lru_cache(maxsize=1)
def get_graph():
    """
    1) Eğer disk'te graph varsa → yükle
    2) Yoksa → indir, diske kaydet
    3) RAM'de cache'le
    """
    if os.path.exists(GRAPH_FILE):
        print("✅ Kocaeli yol ağı diskten yüklendi.")
        G = ox.load_graphml(GRAPH_FILE)
    else:
        print("📥 Kocaeli yol ağı indiriliyor (ilk sefer, yavaş)...")
        G = ox.graph_from_place(
            PLACE_NAME,
            network_type="drive",
            simplify=True
        )
        ox.save_graphml(G, GRAPH_FILE)
        print("💾 Yol ağı diske kaydedildi.")

    return G

# -------------------------------------------------
# SHORTEST PATH (GERÇEK YOL)
# -------------------------------------------------
def shortest_path_coords(
    src_lat: float,
    src_lon: float,
    dst_lat: float,
    dst_lon: float
):
    """
    İki nokta arasındaki gerçek yol koordinatlarını ve
    toplam mesafeyi (metre) döndürür.
    """
    G = get_graph()

    # En yakın yol düğümleri
    orig = ox.nearest_nodes(G, src_lon, src_lat)
    dest = ox.nearest_nodes(G, dst_lon, dst_lat)

    # En kısa yol
    route = nx.shortest_path(G, orig, dest, weight="length")
    length_m = nx.shortest_path_length(G, orig, dest, weight="length")

    # Koordinatlar
    coords = [
        [G.nodes[node]["y"], G.nodes[node]["x"]]
        for node in route
    ]

    return coords, length_m
