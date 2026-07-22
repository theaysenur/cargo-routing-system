/* -------------------------------------------------
   user.js  (SON – HATASIZ & DOĞRU MİMARİ)
------------------------------------------------- */

document.addEventListener("DOMContentLoaded", () => {
  loadScenarios();
  loadStations();
  disableCargoInputs();

  document
    .getElementById("scenarioSelect")
    .addEventListener("change", onScenarioChange);
});

/* -------------------------------------------------
   SENARYO DEĞİŞİNCE
------------------------------------------------- */
function onScenarioChange() {
  const scenarioId = Number(document.getElementById("scenarioSelect").value);

  if (!scenarioId) {
    disableCargoInputs();
    clearCargoStatus();
    clearUserRoutes();
    return;
  }

  enableCargoInputs();
  loadCargoStatus();
  loadUserRoutes(); // ✅ SADECE DB’DEN OKU
}

/* -------------------------------------------------
   INPUT KİLİT / AÇ
------------------------------------------------- */
function enableCargoInputs() {
  ["stationSelect", "cargoCount", "totalWeight", "sendCargoBtn"]
    .forEach(id => document.getElementById(id).disabled = false);
}

function disableCargoInputs() {
  ["stationSelect", "cargoCount", "totalWeight", "sendCargoBtn"]
    .forEach(id => document.getElementById(id).disabled = true);
}

/* -------------------------------------------------
   SENARYOLARI YÜKLE
------------------------------------------------- */
function loadScenarios() {
  const userId = localStorage.getItem("user_id");
  if (!userId) return;

  fetch(`http://127.0.0.1:5000/user/scenarios/${userId}`)
    .then(res => res.json())
    .then(data => {
      const select = document.getElementById("scenarioSelect");
      select.innerHTML = `<option value="">-- Senaryo Seç --</option>`;

      data.forEach(s => {
        const opt = document.createElement("option");
        opt.value = s.id;
        opt.textContent = s.name;
        select.appendChild(opt);
      });
    });
}

/* -------------------------------------------------
   İSTASYONLARI YÜKLE
------------------------------------------------- */
function loadStations() {
  fetch("http://127.0.0.1:5000/admin/stations")
    .then(res => res.json())
    .then(data => {
      const select = document.getElementById("stationSelect");
      select.innerHTML = "";

      data.forEach(s => {
        if (s.name.toLowerCase().includes("umuttepe")) return;
        const opt = document.createElement("option");
        opt.value = s.id;
        opt.textContent = s.name;
        select.appendChild(opt);
      });
    });
}

/* -------------------------------------------------
   SENARYO OLUŞTUR
------------------------------------------------- */
function createScenario() {
  const name = document.getElementById("newScenarioName").value.trim();
  const userId = Number(localStorage.getItem("user_id"));

  if (!name) return alert("Senaryo adı boş olamaz");

  fetch("http://127.0.0.1:5000/admin/scenario", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario_name: name, user_id: userId })
  })
    .then(res => res.json())
    .then(data => {
      document.getElementById("newScenarioName").value = "";
      loadScenarios();

      setTimeout(() => {
        const select = document.getElementById("scenarioSelect");
        select.value = String(data.id);
        select.dispatchEvent(new Event("change"));
      }, 300);
    });
}

/* -------------------------------------------------
   KARGO EKLE
------------------------------------------------- */
function sendCargo() {
  const payload = {
    user_id: Number(localStorage.getItem("user_id")),
    scenario_id: Number(document.getElementById("scenarioSelect").value),
    station_id: Number(document.getElementById("stationSelect").value),
    cargo_count: Number(document.getElementById("cargoCount").value),
    total_weight: Number(document.getElementById("totalWeight").value)
  };

  fetch("http://127.0.0.1:5000/user/cargo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
    .then(() => {
      loadCargoStatus();
      loadUserRoutes();
      document.getElementById("cargoCount").value = 1;
      document.getElementById("totalWeight").value = 0;
    });
}

/* -------------------------------------------------
   KARGO DURUMLARI
------------------------------------------------- */
function loadCargoStatus() {
  const userId = localStorage.getItem("user_id");
  const scenarioId = Number(document.getElementById("scenarioSelect").value);
  const container = document.getElementById("cargoStatus");

  fetch(`http://127.0.0.1:5000/user/cargo/status/${userId}`)
    .then(res => res.json())
    .then(data => {
      container.innerHTML = "";

      const filtered = data.filter(c => c.scenario_id === scenarioId);
      if (!filtered.length) {
        container.innerHTML = "<p>Bu senaryoda kargo yok.</p>";
        return;
      }

      filtered.forEach(c => {
        container.innerHTML += `
          <div class="cargo-card">
            <b>${c.status === "REJECTED" ? "❌" : "✅"} Kargo #${c.cargo_id}</b><br/>
            İstasyon: ${c.station}<br/>
            Ağırlık: ${c.weight} kg<br/>
            Durum: ${c.status}
          </div>
        `;
      });
    });
}

/* -------------------------------------------------
   USER – ROTA BİLGİSİ (SADECE DB OKUMA)
------------------------------------------------- */
function loadUserRoutes() {
  const scenarioId = Number(document.getElementById("scenarioSelect").value);
  const container = document.getElementById("userRouteDetails");

  container.innerHTML = "<p>⏳ Rota kontrol ediliyor...</p>";

  fetch(`http://127.0.0.1:5000/user/routes/${scenarioId}`)
    .then(res => res.json())
    .then(routes => {
      container.innerHTML = "";

      if (!routes || !routes.length) {
        container.innerHTML = "<p>⚠️ Admin henüz rota üretmedi.</p>";
        return;
      }

      routes.forEach((r, i) => {
        container.innerHTML += `
          <div class="cargo-card">
            <b>🚚 Araç ${i + 1}</b><br/>
            Mesafe: ${r.distance_km.toFixed(2)} km<br/>
            Maliyet: ${r.total_cost.toFixed(2)} ₺<br/>
            <b>Güzergâh:</b><br/>
            ${r.route.join(" → ")}
          </div>
        `;
      });
    });
}

/* -------------------------------------------------
   TEMİZLEME
------------------------------------------------- */
function clearUserRoutes() {
  document.getElementById("userRouteDetails").innerHTML = "";
}

function clearCargoStatus() {
  document.getElementById("cargoStatus").innerHTML = "";
}
