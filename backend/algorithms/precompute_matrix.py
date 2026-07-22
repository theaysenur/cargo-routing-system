import pickle
import osmnx as ox
import networkx as nx
from algorithms.stations import STATIONS

# -------------------------------------------------
# İSİM NORMALİZASYONU (route_planner ile AYNI)
# -------------------------------------------------
def normalize_name(name: str) -> str:
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
# DEPOT (NORMALIZE)
# -------------------------------------------------
DEPOT = STATIONS["Depot"]
DEPOT_NAME = normalize_name("Izmit")

DIST = 40000  # 40 km → Kocaeli için yeterli

print("Graph oluşturuluyor...")
G = ox.graph_from_point(
    center_point=DEPOT,
    dist=DIST,
    network_type="drive",
    simplify=True
)

# -------------------------------------------------
# NODE EŞLEŞTİRME (NORMALIZE KEY)
# -------------------------------------------------
print("Node eşleştirme...")
nodes = {}

for name, (lat, lon) in STATIONS.items():
    n_name = normalize_name(name)
    nodes[n_name] = ox.nearest_nodes(G, lon, lat)

# -------------------------------------------------
# MESAFE MATRİSİ
# -------------------------------------------------
print("Mesafe matrisi hesaplanıyor...")
distance_matrix = {}

for a_name, a_node in nodes.items():
    lengths = nx.single_source_dijkstra_path_length(
        G, a_node, weight="length"
    )

    distance_matrix[a_name] = {}

    for b_name, b_node in nodes.items():
        distance_matrix[a_name][b_name] = float(
            lengths.get(b_node, float("inf"))
        )

# -------------------------------------------------
# KAYDET
# -------------------------------------------------
with open("algorithms/distance_matrix.pkl", "wb") as f:
    pickle.dump(distance_matrix, f)

print("DONE ✅ distance_matrix.pkl normalize edilerek oluşturuldu")
