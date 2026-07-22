### 🚀 Kurulum

**Gereksinimler:** Python 3.10+, Microsoft SQL Server, ODBC Driver 17

1. Depoyu klonlayın:
```bash
git clone https://github.com/theaysenur/cargo-routing-system.git
cd cargo-routing-system/backend
```

2. Bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
```

3. SQL Server'da `CargoRoutingDB` veritabanını oluşturun.

4. `config.py` dosyasındaki bağlantı bilgilerini düzenleyin.

5. Uygulamayı başlatın:
```bash
python app.py
```

6. Tarayıcıda `http://localhost:5000` adresine gidin.

---

## 🇬🇧 English

### About
A web-based cargo routing and logistics optimization system designed for Kocaeli province, Turkey. The system leverages real road network data from OpenStreetMap (via OSMnx), precomputed distance matrices, and a capacity-constrained greedy heuristic algorithm to calculate optimal delivery routes across 12 district stations.

The routing engine supports multiple vehicle types with varying capacities (1000kg, 750kg, 500kg) and automatically assigns rental vehicles when fleet capacity is exceeded. Routes are visualized on an interactive Leaflet.js map with color-coded paths and detailed cost analysis per scenario.

### ✨ Features
- Greedy heuristic route optimization with capacity-constrained vehicle assignment
- Real Kocaeli road network from OpenStreetMap via OSMnx (GraphML)
- Precomputed distance matrix (pickle) for high-performance route calculation
- Multiple vehicle types with rental cost optimization
- Interactive route visualization on Leaflet.js maps with color-coded paths
- Admin and user panels with authentication
- SQL Server database integration
- Scenario-based cost analysis and summary reporting

### 🚀 Getting Started

**Requirements:** Python 3.10+, Microsoft SQL Server, ODBC Driver 17

```bash
git clone https://github.com/theaysenur/cargo-routing-system.git
cd cargo-routing-system/backend
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:5000` in your browser.

## 👥 Katkıda Bulunanlar / Contributors
Bu projedeki kodun geliştirilmesi ve iyileştirilmesi aşağıdaki kişiler tarafından ortaklaşa gerçekleştirilmiştir:

- [Ayşenur Karaaslan](https://github.com/theaysenur)
- [ARKADAŞIN_ADI](https://github.com/ARKADAŞIN_GITHUB)

## 📄 Lisans / License
Bu proje eğitim amaçlıdır (Kocaeli Üniversitesi, Yazılım Laboratuvarı II).
