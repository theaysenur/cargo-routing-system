// -------------------------------------------------
// user_map.js  (ÇALIŞAN ve DOĞRU SÜRÜM)
// -------------------------------------------------

let userMap;
let stationLayer;
let routeLayer;

const ROUTE_COLORS = [
  "#005eff",
  "#2ecc71",
  "#e74c3c",
  "#9b59b6",
  "#f39c12",
  "#1abc9c",
  "#34495e"
];

document.addEventListener("DOMContentLoaded", () => {

  userMap = L.map("map").setView([40.7667, 29.9167], 9);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap"
  }).addTo(userMap);

  stationLayer = L.layerGroup().addTo(userMap);
  routeLayer   = L.layerGroup().addTo(userMap);

  loadStationMarkers();

  document
    .getElementById("scenarioSelect")
    .addEventListener("change", drawScenarioRoute);
});

// -------------------------------------------------
// 📍 İSTASYON NOKTALARI (SABİT)
// -------------------------------------------------
function loadStationMarkers() {
  fetch("http://127.0.0.1:5000/admin/stations")
    .then(res => res.json())
    .then(stations => {
      stationLayer.clearLayers();

      stations.forEach(s => {
        L.circleMarker([s.lat, s.lon], {
          radius: 6,
          color: "#333",
          fillColor: "#ffcc00",
          fillOpacity: 0.9
        })
          .bindPopup(s.name)
          .addTo(stationLayer);
      });
    });
}

// -------------------------------------------------
// 🛣 GERÇEK YOL (ADMIN NASIL ÇİZDİYSE AYNI)
// -------------------------------------------------
// -------------------------------------------------
// 🛣 USER İÇİN GERÇEK YOL (ADMIN SONUCUNDAN OKUMA)
// -------------------------------------------------
function drawScenarioRoute() {
  const scenarioId = document.getElementById("scenarioSelect").value;
  if (!scenarioId) return;

  routeLayer.clearLayers();

  // ✅ ARTIK admin/route ÇAĞRISI YOK!
  fetch(`http://127.0.0.1:5000/user/routes/${scenarioId}`)
    .then(res => res.json())
    .then(routes => {
      if (!Array.isArray(routes) || routes.length === 0) {
        alert("Admin bu senaryo için henüz rota üretmedi.");
        return;
      }

      let allCoords = [];

      routes.forEach((r, index) => {
        // backend farklı isim döndürebilir: polyline / path_coords vs.
        const poly = r.polyline || r.path_coords || r.coords;
        if (!poly || poly.length < 2) return;

        const color = ROUTE_COLORS[index % ROUTE_COLORS.length];

        L.polyline(poly, {
          color,
          weight: 5,
          opacity: 0.9
        }).addTo(routeLayer);

        allCoords.push(...poly);
      });

      if (allCoords.length > 0) {
        userMap.fitBounds(allCoords, { padding: [40, 40] });
      }
    })
    .catch(err => {
      console.error(err);
      alert("Rota okunamadı.");
    });
}
