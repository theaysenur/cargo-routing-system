// =================================================
// GLOBAL
// =================================================

// =================================================
// CUSTOM STATION ICON
// =================================================
const stationPinIcon = L.icon({
  iconUrl: "/images/konum.png",
  iconSize: [32, 32],
  iconAnchor: [16, 32],
  popupAnchor: [0, -30]
});


let map;
let routeLayers = [];
let stationMarkers = [];

const ROUTE_COLORS = ["#ef4444", "#3b82f6", "#22c55e", "#a855f7"];

// =================================================
// BAŞLAT
// =================================================
document.addEventListener("DOMContentLoaded", () => {
  initMap();
  loadScenarios();
   loadScenarioSummary();
});

// =================================================
// HARİTA
// =================================================
function initMap() {
  map = L.map("map").setView([40.76, 29.92], 9);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap"
  }).addTo(map);

  // 🔥 FLEX FIX
  setTimeout(() => {
    map.invalidateSize();
  }, 300);

  loadStations();
}

function showRouteDetail(route, index) {
  const panel = document.getElementById("routeDetailPanel");

  // aynı rotaya tekrar tıklandıysa kapat
  if (panel.dataset.active === String(index)) {
    panel.style.display = "none";
    panel.dataset.active = "";
    return;
  }

  panel.dataset.active = index;
  panel.style.display = "block";

  const capacityUsage = ((route.carried_weight / route.capacity) * 100).toFixed(1);

  panel.innerHTML = `
    <b>🚚 Araç ${index + 1}</b><br/>
    <b>Kapasite:</b> ${route.capacity} kg<br/>
    <b>Taşınan:</b> ${route.carried_weight.toFixed(1)} kg<br/>
    <b>Kapasite Kullanımı:</b> %${capacityUsage}<br/><br/>

    <b>Mesafe:</b> ${route.distance_km.toFixed(2)} km<br/>
    <b>Yol Maliyeti:</b> ${route.road_cost.toFixed(2)} ₺<br/>
    ${route.rental_cost > 0 ? `<b>Kiralama:</b> ${route.rental_cost} ₺<br/>` : ""}
    <b>Toplam Maliyet:</b> ${route.total_cost.toFixed(2)} ₺
  `;
}


// =================================================
// İSTASYONLAR
// =================================================
function clearStationMarkers() {
  stationMarkers.forEach(m => map.removeLayer(m));
  stationMarkers = [];
}

function loadStations() {
  fetch("http://127.0.0.1:5000/admin/stations")
    .then(res => res.json())
    .then(stations => {
      clearStationMarkers();

      const coords = [];

      stations.forEach(s => {
        const marker = L.circleMarker([s.lat, s.lon], {
          radius: 8,
          color: "#1e40af",        // dış çizgi
          fillColor: "#3b82f6",    // iç renk (mavi pin hissi)
          fillOpacity: 1,
          weight: 2
        })
          .addTo(map)
          .bindPopup(`
            <b>${s.name}</b><br/>
            (${s.lat.toFixed(4)}, ${s.lon.toFixed(4)})
          `);

        stationMarkers.push(marker);
        coords.push([s.lat, s.lon]);
      });

      // Haritayı tüm istasyonlara göre ayarla
      if (coords.length > 0) {
        map.fitBounds(coords, { padding: [40, 40] });
      }
    })
    .catch(err => {
      console.error("Station load error:", err);
    });
}



// =================================================
// ➕ YENİ İSTASYON EKLE (ADMIN)
// =================================================
function addStation() {
  const name = document.getElementById("newStationName").value.trim();
  const lat  = document.getElementById("newStationLat").value;
  const lon  = document.getElementById("newStationLon").value;
  const msg  = document.getElementById("stationAddMsg");

  if (!name || !lat || !lon) {
    msg.innerText = "❌ Tüm alanlar zorunlu";
    return;
  }

  fetch("http://127.0.0.1:5000/admin/stations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, lat, lon })
  })
    .then(res => res.json().then(data => ({ ok: res.ok, data })))
    .then(({ ok, data }) => {
      if (!ok) throw new Error(data.error || "İstasyon eklenemedi");

      msg.innerText = "✅ İstasyon eklendi";

      // input temizle
      document.getElementById("newStationName").value = "";
      document.getElementById("newStationLat").value  = "";
      document.getElementById("newStationLon").value  = "";

      // 🔥 HARİTAYI GÜNCELLE
      loadStations();
    })
    .catch(err => {
      msg.innerText = "❌ " + err.message;
    });
}

// =================================================
// SENARYOLAR
// =================================================
function loadScenarios() {
  fetch("http://127.0.0.1:5000/admin/scenarios")
    .then(res => res.json())
    .then(data => {
      const select = document.getElementById("scenarioSelect");
      select.innerHTML = '<option value="">Senaryo seç</option>';

      data.forEach(s => {
        const opt = document.createElement("option");
        opt.value = s.id;
        opt.textContent = s.name;
        select.appendChild(opt);
      });
    });
}

// =================================================
// SENARYO ÇALIŞTIR
// =================================================
function runScenario() {
  const scenarioId = document.getElementById("scenarioSelect").value;
  const mode = document.getElementById("modeSelect").value;
  const cargoMode = document.getElementById("cargoModeSelect").value;

  localStorage.setItem("last_mode", mode);
  localStorage.setItem("last_cargo_mode", cargoMode);

  if (!scenarioId) {
    alert("Lütfen senaryo seç");
    return;
  }

  fetch(
    `http://127.0.0.1:5000/admin/route/${scenarioId}?mode=${mode}&cargo_mode=${cargoMode}`
  )
    .then(res => {
      if (!res.ok) {
        throw new Error("Backend hata döndü");
      }
      return res.json();
    })
    .then(data => {
      clearRoutes();

      if (!data.routes || data.routes.length === 0) {
        alert("Rota üretilemedi");
        return;
      }

      // 📊 Üst özet
      updateStats(data);

      // 🗺 Rotalar (tıklanabilir)
      drawRoutes(data.routes);

      // 🎨 Legend
      updateLegend(data.routes);

      // 📋 Sol panel rota detayları
      renderRouteDetails(data.routes);

      if (mode === "LIMITED" && data.rejected?.length) {
        alert(`⚠️ ${data.rejected.length} kargo reddedildi (kapasite yetersiz).`);
      }
    })
    .catch(err => {
      console.error("Scenario run error:", err);
      alert("Senaryo çalıştırılırken hata oluştu");
    });
}


// =================================================
// ROTA ÇİZ
// =================================================
function drawRoutes(routes) {
  let allCoords = [];

  routes.forEach((r, i) => {
    if (!r.polyline || r.polyline.length < 2) return;

    const line = L.polyline(r.polyline, {
      color: ROUTE_COLORS[i % ROUTE_COLORS.length],
      weight: 5,
      opacity: 0.9
    })
    .addTo(map)
    .on("click", () => {
      showRouteDetail(r, i);   // 🔥 TIKLANINCA AÇ
    });

    routeLayers.push(line);
    allCoords.push(...r.polyline);
  });

  if (allCoords.length > 0) {
    map.fitBounds(allCoords, { padding: [40, 40] });
  }
}
function toggleRouteDetail(i) {
  const el = document.getElementById(`routeDetail_${i}`);
  if (!el) return;
  el.style.display = (el.style.display === "none" || el.style.display === "")
    ? "block"
    : "none";
}

function renderRouteDetails(routes) {
  const box = document.getElementById("routeDetails");
  if (!box) {
    console.error("routeDetails div bulunamadı. admin.html içine <div id='routeDetails'></div> ekle.");
    return;
  }

  box.innerHTML = "";

  if (!Array.isArray(routes) || routes.length === 0) {
    box.innerHTML = `<div style="color:#94a3b8; font-size:13px;">Rota detayı yok</div>`;
    return;
  }

  routes.forEach((r, i) => {
    // ✅ pretty_route güvenli
    const routeText = Array.isArray(r.route) && r.route.length > 0
  ? r.route.join(" → ")
  : "Rota bilgisi yok";

    // ✅ sayısal alanlar güvenli
    const capacity = (r.capacity ?? "-");
    const distance = Number(r.distance_km ?? 0).toFixed(1);
    const carried  = Number(r.carried_weight ?? 0).toFixed(1);
    const roadCost = Number(r.road_cost ?? 0).toFixed(2);
    const rental   = Number(r.rental_cost ?? 0);
    const rentalCost = rental.toFixed(2);
    const totalCost = Number(r.total_cost ?? (Number(r.road_cost ?? 0) + rental)).toFixed(2);

    const card = document.createElement("div");
    card.className = "cargo-card";

    card.innerHTML = `
      <div style="cursor:pointer; font-weight:bold;"
           onclick="toggleRouteDetail(${i})">
        🚚 Araç ${i + 1} (${capacity} kg) – ${distance} km
      </div>

      <div id="routeDetail_${i}" style="display:none; margin-top:8px;">
        <div><b>Güzergâh:</b></div>
        <div style="margin-left:10px; color:#93c5fd;">
          ${routeText}
        </div>

        <div style="margin-top:6px;">
          <b>Taşınan Ağırlık:</b> ${carried} kg<br/>
          <b>Yol Maliyeti:</b> ${roadCost} ₺<br/>
          ${rental > 0 ? `<b>Kiralama:</b> ${rentalCost} ₺<br/>` : ""}
          <b>Toplam:</b> ${totalCost} ₺
        </div>
      </div>
    `;

    box.appendChild(card);
  });
}


function showRouteDetail(i) {
  const el = document.getElementById(`routeDetail_${i}`);
  if (!el) return;

  el.style.display = el.style.display === "none" ? "block" : "none";
}



// =================================================
// TEMİZLE
// =================================================
function clearRoutes() {
  routeLayers.forEach(l => map.removeLayer(l));
  routeLayers = [];
}

// =================================================
// İSTATİSTİK
// =================================================
function updateStats(data) {
  document.getElementById("routeCount").textContent =
    data.vehicle_count;

  document.getElementById("totalKm").textContent =
    data.total_distance_km.toFixed(2);

  document.getElementById("totalCost").textContent =
    data.total_cost.toFixed(2);
}

// =================================================
// LEGEND
// =================================================
function updateLegend(routes) {
  const legend = document.getElementById("legend");
  legend.innerHTML = "";

  routes.forEach((r, i) => {
    const row = document.createElement("div");
    row.className = "legend-item";

    row.innerHTML = `
      <span class="legend-color"
        style="background:${ROUTE_COLORS[i % ROUTE_COLORS.length]}"></span>
      Araç ${i + 1} – ${r.distance_km.toFixed(1)} km
    `;

    legend.appendChild(row);
  });
}
let summaryChart = null;

function loadScenarioSummary() {
  fetch("http://127.0.0.1:5000/admin/scenarios/summary")
    .then(res => res.json())
    .then(data => {
      renderSummaryTable(data);
      renderSummaryChart(data);
    })
    .catch(err => console.error("Summary fetch error:", err));
}

/* -----------------------------
   TABLO
----------------------------- */
function renderSummaryTable(data) {
  const tbody = document.querySelector("#summaryTable tbody");
  tbody.innerHTML = "";

  data.forEach(s => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${s.scenario_id}</td>
      <td>${s.scenario_name}</td>
      <td>${s.vehicle_count}</td>
      <td>${s.total_distance_km.toFixed(1)}</td>
      <td>${s.total_cost.toFixed(1)}</td>
      <td>${s.user_count}</td>
      <td>${s.rejected_count}</td>
      <td>
        <button style="padding:4px 8px;font-size:11px;"
                onclick="showScenarioDetail(${s.scenario_id})">
          Gör
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

/* -----------------------------
   GRAFİK
----------------------------- */
function renderSummaryChart(data) {
  const ctx = document.getElementById("summaryChart");

  const labels = data.map(s => s.scenario_name);
  const costs  = data.map(s => s.total_cost);

  if (summaryChart) summaryChart.destroy();

  summaryChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Toplam Maliyet",
        data: costs,
        backgroundColor: "#60a5fa"
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: { beginAtZero: true }
      }
    }
  });
}

/* -----------------------------
   DETAY ALANI
----------------------------- */
function showScenarioDetail(scenarioId) {
  const box = document.getElementById("scenarioDetails");
  box.innerHTML = "<p>⏳ Senaryo detayı yükleniyor...</p>";

  fetch(`http://127.0.0.1:5000/admin/route/${scenarioId}?mode=UNLIMITED&cargo_mode=MAX_WEIGHT`)
    .then(res => res.json())
    .then(data => {

      if (!data.routes || data.routes.length === 0) {
        box.innerHTML = "<p>⚠️ Bu senaryoya ait rota yok.</p>";
        return;
      }

      let html = "";

      data.routes.forEach((r, i) => {
        html += `
          <div class="route-card">
            <div class="route-head">
              🚚 Araç ${i + 1}
              <span>${r.distance_km.toFixed(1)} km</span>
            </div>
            <div class="route-body">
              <div class="route-row"><b>Maliyet:</b> ${r.total_cost.toFixed(1)} birim</div>
              <div class="route-row"><b>Kapasite:</b> ${r.capacity}</div>
              <div class="route-row"><b>Taşınan:</b> ${r.carried_weight} kg</div>
              <div class="route-row">
                <b>Güzergâh:</b><br/>
                ${r.route.join(" → ")}
              </div>
            </div>
          </div>
        `;
      });

      box.innerHTML = html;
    })
    .catch(err => {
      console.error(err);
      box.innerHTML = "<p>❌ Senaryo detayı alınamadı.</p>";
    });
}
