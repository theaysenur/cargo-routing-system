import matplotlib
matplotlib.use("Agg")  # ❗ GUI backend KAPALI

import matplotlib.pyplot as plt
import os


def plot_costs(summary, filename="vehicle_costs.png"):
    vehicles = [r["vehicle"] for r in summary]
    costs = [r["total_cost"] for r in summary]

    plt.figure()
    plt.bar(vehicles, costs)
    plt.xlabel("Araç")
    plt.ylabel("Toplam Maliyet")
    plt.title("Araç Bazlı Toplam Maliyet")

    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

    print(f"Grafik kaydedildi: {os.path.abspath(filename)}")
