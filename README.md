# Cargo Routing & Logistics System 🚚📍

`Python` `Flask` `NetworkX` `OSMnx` `Leaflet.js` `SQL Server`

Kocaeli ili için gerçek yol ağı verisi kullanan, sezgisel (heuristic) algoritma tabanlı kargo rotalama ve lojistik optimizasyon sistemi.



## Proje Hakkında
Bu proje, Kocaeli ilinin gerçek yol ağı üzerinde kargo dağıtım rotalarını optimize eden web tabanlı bir lojistik sistemdir. OpenStreetMap verileri üzerinden OSMnx ile oluşturulan GraphML yol ağı, önceden hesaplanmış mesafe matrisi ve kapasite kısıtlı araç atama algoritmaları ile en verimli rotaları hesaplar. Sistem, 12 ilçe istasyonu arasında farklı araç kapasiteleri ve kiralama maliyetlerini dikkate alarak optimum dağıtım planı oluşturur.

Kocaeli Üniversitesi Bilgisayar Mühendisliği — Yazılım Laboratuvarı II dersi kapsamında geliştirilmiştir.

## ✨ Özellikler
- **Sezgisel Rota Optimizasyonu:** Greedy heuristic algoritma ile kapasite kısıtlı araç atama. Her araç için yük kapasitesi ve maliyet analizi yapılarak en verimli dağıtım rotaları hesaplanır. Algoritma, istasyonları değer/mesafe yoğunluğuna göre sıralayarak en karlı teslimat sırasını belirler.
- **Gerçek Yol Ağı:** OpenStreetMap üzerinden OSMnx ile indirilen Kocaeli ili yol ağı GraphML formatında saklanır. Gerçek yol mesafeleri ve trafik yapısı dikkate alınarak kuş uçuşu değil, gerçek sürüş mesafeleri üzerinden hesaplama yapılır.
- **Önceden Hesaplanmış Mesafe Matrisi:** Tüm istasyonlar arası mesafeler pickle formatında önbelleğe alınarak, rota hesaplamalarında yüksek performans sağlanır. İsim normalizasyonu ile Türkçe karakter uyumsuzlukları otomatik çözülür.
- **Çoklu Araç Yönetimi:** Üç farklı kapasitede araç tipi (V1: 1000kg, V2: 750kg, V3: 500kg) desteklenir. Mevcut filo kapasitesi aşıldığında otomatik olarak kiralık araç (500kg, 200₺ kiralama ücreti) atanır.
- **İnteraktif Harita:** Leaflet.js ile hesaplanan rotalar, istasyonlar ve araç güzergahları renk kodlu olarak harita üzerinde görselleştirilir. Her rota farklı renkte çizilerek araçların güzergahları kolayca ayırt edilir.
- **Admin & Kullanıcı Panelleri:** Yönetici panelinden senaryo oluşturma, rota planlama, maliyet analizi ve özet raporlama; kullanıcı panelinden kargo takibi ve teslimat durumu görüntüleme yapılabilir.
- **Kimlik Doğrulama:** Kullanıcı kayıt ve giriş sistemi ile güvenli erişim kontrolü. Admin ve kullanıcı rolleri ayrıştırılmıştır.
- **Senaryo Bazlı Maliyet Raporlama:** Her senaryo için toplam mesafe (km), km başına maliyet, araç kiralama ücreti ve toplam maliyet detaylı olarak raporlanır. Farklı senaryolar karşılaştırılarak en ekonomik plan belirlenebilir.

## 🛠️ Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| Backend | Python, Flask, Flask-CORS |
| Algoritmalar | NetworkX, OSMnx, Greedy Heuristic |
| Frontend | HTML/CSS, JavaScript, Leaflet.js |
| Veritabanı | Microsoft SQL Server (pyodbc) |
| Veri İşleme | Pandas, NumPy, GeoPandas |
| Görselleştirme | Folium, Matplotlib |

## 🏗️ Sistem Mimarisi
Sistem üç temel katmandan oluşur:

**Algoritma Katmanı:** OSMnx ile Kocaeli ili yol ağı yönetimi, Dijkstra tabanlı en kısa yol hesaplama, tüm istasyonlar arası mesafe matrisi ön hesaplama (`precompute_matrix.py`), greedy heuristic ile kapasite kısıtlı araç-rota ataması (`vehicle_planner.py`), km bazlı maliyet hesaplama (`route_costs.py`) ve İzmit, Gebze, Darıca, Çayırova, Dilovası, Derince, Körfez, Kartepe, Gölcük, Başiskele, Karamürsel, Kandıra istasyonlarının koordinat yönetimini (`stations.py`) kapsar.

**API Katmanı:** Flask Blueprint yapısında organize edilmiş REST API endpoint'leri. Admin paneli için senaryo oluşturma, rota planlama ve maliyet analizi (`admin_routes.py`), kullanıcı kargo takip işlemleri (`user_routes.py`) ve JWT tabanlı kimlik doğrulama (`auth_routes.py`) modülleri içerir. Tüm endpoint'ler CORS desteği ile frontend'e hizmet verir.

**Sunum Katmanı:** Leaflet.js tabanlı interaktif harita görselleştirme, OpenStreetMap tile katmanı, özel istasyon pin ikonları, renk kodlu rota çizimi (kırmızı, mavi, yeşil, mor), senaryo bazlı özet panelleri ve responsive admin/kullanıcı arayüzleri içeren web katmanı.

## 📁 Proje Yapısı

## 🚀 Kurulum

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

3. SQL Server'da `CargoRoutingDB` veritabanını oluşturun ve gerekli tabloları migrate edin.

4. `config.py` dosyasındaki bağlantı bilgilerini kendi ortamınıza göre düzenleyin:
```python
DB_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=CargoRoutingDB;"
    "Trusted_Connection=yes;"
)
```

5. Mesafe matrisini ön hesaplayın (ilk çalıştırmada gerekli):
```bash
python algorithms/precompute_matrix.py
```

6. Uygulamayı başlatın:
```bash
python app.py
```

7. Tarayıcıda `http://localhost:5000` adresine gidin.

## 👥 Katkıda Bulunanlar
Bu projedeki kodun geliştirilmesi ve iyileştirilmesi aşağıdaki kişiler tarafından ortaklaşa gerçekleştirilmiştir. Kodlama, hata ayıklama ve algoritma uygulaması dahil olmak üzere tüm teknik aşamalar ortak çaba ile tamamlanmıştır.

- [Ayşenur Karaaslan](https://github.com/theaysenur)
- [Zeynep Vuslat Solmaz](https://github.com/zvsolmaz)

## 📄 Lisans
Bu proje eğitim amaçlıdır (Kocaeli Üniversitesi, Yazılım Laboratuvarı II).
