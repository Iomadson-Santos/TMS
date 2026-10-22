import { api } from "./api.js";
import { escapeHtml, formatNumber } from "./format.js";
import { initLayout } from "./layout.js";
import { setButtonLoading, showToast } from "./ui.js";

const DEFAULT_CENTER = [-23.5505, -46.6333];
const REFRESH_INTERVAL_MS = 15000;

let liveItems = [];
let selectedRouteId = null;
let map = null;
let liveLayer = null;
let historyLayer = null;
let refreshTimer = null;
let websocket = null;
let websocketRetryTimer = null;
let websocketPingTimer = null;
let hasFittedMap = false;
let reloadScheduled = false;

function formatClock(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(date);
}

function relativeSignal(item) {
  if (item.seconds_since_update == null) return "Sem posição";
  const seconds = Number(item.seconds_since_update);
  if (seconds < 10) return "Agora";
  if (seconds < 60) return `Há ${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `Há ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return `Há ${hours}h`;
}

function progressPercent(item) {
  const total = Number(item.deliveries_total || 0);
  const completed = Number(item.deliveries_completed || 0);
  return total ? Math.round((completed / total) * 100) : 0;
}

function speedLabel(item) {
  return item.speed_kmh == null ? "—" : `${formatNumber(item.speed_kmh, 0)} km/h`;
}

function accuracyLabel(item) {
  return item.accuracy_m == null ? "—" : `± ${formatNumber(item.accuracy_m, 0)} m`;
}

function hasCoordinates(item) {
  return Number.isFinite(Number(item.latitude)) && Number.isFinite(Number(item.longitude));
}

function currentFilteredItems() {
  const search = document.getElementById("trackingSearch").value.trim().toLowerCase();
  const signal = document.getElementById("trackingSignalFilter").value;

  return liveItems.filter((item) => {
    const text = [item.driver_name, item.route_name, item.vehicle_plate]
      .join(" ")
      .toLowerCase();
    const matchesSearch = !search || text.includes(search);
    const matchesSignal =
      !signal ||
      (signal === "online" && item.is_online) ||
      (signal === "offline" && !item.is_online);
    return matchesSearch && matchesSignal;
  });
}

function renderStats() {
  const online = liveItems.filter((item) => item.is_online).length;
  document.getElementById("trackingActiveRoutes").textContent = liveItems.length;
  document.getElementById("trackingOnlineDrivers").textContent = online;
  document.getElementById("trackingOfflineDrivers").textContent = liveItems.length - online;
  document.getElementById("trackingLastRefresh").textContent = formatClock();
}

function renderDrivers() {
  const list = document.getElementById("trackingDriversList");
  const filtered = currentFilteredItems();
  document.getElementById("trackingDriverCount").textContent =
    `${filtered.length} motorista${filtered.length === 1 ? "" : "s"}`;

  if (!filtered.length) {
    list.innerHTML = `
      <div class="tracking-empty">
        <div>
          <strong>Nenhum motorista encontrado</strong>
          <span>Inicie uma rota ou altere os filtros para visualizar o rastreamento.</span>
        </div>
      </div>
    `;
    return;
  }

  list.innerHTML = filtered
    .map((item) => {
      const progress = progressPercent(item);
      const selected = Number(selectedRouteId) === Number(item.route_id);
      const signalText = item.is_online ? "GPS online" : "Sem sinal";
      return `
        <button
          class="tracking-driver-card ${selected ? "selected" : ""}"
          type="button"
          data-tracking-route="${item.route_id}"
        >
          <span class="tracking-driver-top">
            <span>
              <span class="tracking-driver-name">${escapeHtml(item.driver_name)}</span>
              <span class="tracking-driver-route">${escapeHtml(item.route_name)} • ${escapeHtml(
                item.vehicle_plate
              )}</span>
            </span>
            <span class="tracking-signal ${item.is_online ? "online" : ""}">
              ${escapeHtml(signalText)}
            </span>
          </span>

          <span class="tracking-driver-grid">
            <span>
              <small>Último sinal</small>
              <strong>${escapeHtml(relativeSignal(item))}</strong>
            </span>
            <span>
              <small>Velocidade</small>
              <strong>${escapeHtml(speedLabel(item))}</strong>
            </span>
            <span>
              <small>Precisão</small>
              <strong>${escapeHtml(accuracyLabel(item))}</strong>
            </span>
            <span>
              <small>Paradas</small>
              <strong>${item.deliveries_completed}/${item.deliveries_total}</strong>
            </span>
          </span>

          <span class="tracking-progress-row">
            <span>Progresso da rota</span>
            <strong>${progress}%</strong>
          </span>
          <span class="tracking-progress-track"><span style="width:${progress}%"></span></span>

          <span class="tracking-next-stop">
            <strong>Próxima parada:</strong>
            ${escapeHtml(item.next_stop_customer || "Todas as paradas finalizadas")}
          </span>
        </button>
      `;
    })
    .join("");
}

function markerIcon(item) {
  const initial = escapeHtml(String(item.driver_name || "M").charAt(0).toUpperCase());
  return window.L.divIcon({
    className: "tracking-map-pin-wrap",
    html: `<div class="tracking-map-pin ${item.is_online ? "online" : ""}"><span>${escapeHtml(initial)}</span></div>`,
    iconSize: [31, 31],
    iconAnchor: [15, 28],
    popupAnchor: [0, -27],
  });
}

function markerPopup(item) {
  return `
    <div class="tracking-popup">
      <strong>${escapeHtml(item.driver_name)}</strong>
      <span>${escapeHtml(item.route_name)} • ${escapeHtml(item.vehicle_plate)}</span>
      <span>${escapeHtml(item.is_online ? "GPS online" : "Sem sinal recente")} • ${escapeHtml(
        relativeSignal(item)
      )}</span>
      <span>Velocidade: ${escapeHtml(speedLabel(item))}</span>
    </div>
  `;
}

function initializeMap() {
  if (!window.L) {
    document.getElementById("trackingMapFallback").hidden = false;
    document.getElementById("fitTrackingMap").disabled = true;
    return;
  }

  map = window.L.map("trackingMap", {
    zoomControl: true,
    preferCanvas: true,
  }).setView(DEFAULT_CENTER, 10);

  const tileLayer = window.L.tileLayer(
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      maxZoom: 19,
      updateWhenIdle: true,
      crossOrigin: true,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }
  );

  tileLayer.on("tileerror", () => {
    document.getElementById("trackingMapFallback").hidden = false;
  });

  tileLayer.on("load", () => {
    document.getElementById("trackingMapFallback").hidden = true;
  });

  tileLayer.addTo(map);

  liveLayer = window.L.layerGroup().addTo(map);
  historyLayer = window.L.layerGroup().addTo(map);
}

function renderMapMarkers() {
  if (!map || !liveLayer) return;
  liveLayer.clearLayers();

  const coordinates = [];
  for (const item of liveItems) {
    if (!hasCoordinates(item)) continue;
    const latLng = [Number(item.latitude), Number(item.longitude)];
    coordinates.push(latLng);
    const marker = window.L.marker(latLng, { icon: markerIcon(item) })
      .bindPopup(markerPopup(item))
      .on("click", () => selectRoute(item.route_id, { loadHistory: true }));
    marker.addTo(liveLayer);
  }

  if (!hasFittedMap && coordinates.length) {
    fitAllMarkers();
    hasFittedMap = true;
  }
}

function fitAllMarkers() {
  if (!map) return;
  const coordinates = liveItems
    .filter(hasCoordinates)
    .map((item) => [Number(item.latitude), Number(item.longitude)]);

  if (!coordinates.length) {
    map.setView(DEFAULT_CENTER, 10);
    return;
  }
  if (coordinates.length === 1) {
    map.setView(coordinates[0], 15);
    return;
  }
  map.fitBounds(coordinates, { padding: [45, 45], maxZoom: 15 });
}

function selectedItem() {
  return liveItems.find((item) => Number(item.route_id) === Number(selectedRouteId));
}

function renderSelectedSummary(item) {
  const summary = document.getElementById("trackingSelectedSummary");
  if (!item) {
    summary.hidden = true;
    summary.innerHTML = "";
    document.getElementById("trackingMapSubtitle").textContent =
      "Selecione um motorista para ver o trajeto.";
    return;
  }

  summary.hidden = false;
  summary.innerHTML = `
    <div><small>Motorista</small><strong>${escapeHtml(item.driver_name)}</strong></div>
    <div><small>Rota</small><strong>${escapeHtml(item.route_name)}</strong></div>
    <div><small>Último sinal</small><strong>${escapeHtml(formatDateTime(item.captured_at))}</strong></div>
    <div><small>Próxima parada</small><strong>${escapeHtml(
      item.next_stop_customer || "Finalizada"
    )}</strong></div>
  `;
  document.getElementById("trackingMapSubtitle").textContent =
    `${item.driver_name} • ${item.vehicle_plate} • histórico do trajeto`;
}

async function loadHistory(routeId) {
  if (!historyLayer || !map) return;
  historyLayer.clearLayers();

  try {
    const positions = await api(`/tracking/routes/${routeId}/history?limit=1000`);
    const points = (positions || [])
      .filter((position) =>
        Number.isFinite(Number(position.latitude)) && Number.isFinite(Number(position.longitude))
      )
      .map((position) => [Number(position.latitude), Number(position.longitude)]);

    if (points.length >= 2) {
      window.L.polyline(points, {
        weight: 4,
        opacity: 0.8,
      }).addTo(historyLayer);
    }

    if (points.length) {
      window.L.circleMarker(points[0], {
        radius: 6,
        weight: 2,
        fillOpacity: 1,
      })
        .bindTooltip("Início do trajeto")
        .addTo(historyLayer);

      if (points.length === 1) map.setView(points[0], 15);
      else map.fitBounds(points, { padding: [45, 45], maxZoom: 16 });
    } else {
      const item = selectedItem();
      if (item && hasCoordinates(item)) {
        map.setView([Number(item.latitude), Number(item.longitude)], 15);
      }
    }
  } catch (error) {
    showToast(`Não foi possível carregar o histórico: ${error.message}`, "warning", 5000);
  }
}

function selectRoute(routeId, { loadHistory: shouldLoadHistory = true } = {}) {
  selectedRouteId = Number(routeId);
  const item = selectedItem();
  renderDrivers();
  renderSelectedSummary(item);

  if (item && hasCoordinates(item) && map) {
    map.panTo([Number(item.latitude), Number(item.longitude)]);
  }
  if (shouldLoadHistory) loadHistory(selectedRouteId);
}

function renderAll() {
  renderStats();
  renderDrivers();
  renderMapMarkers();

  if (selectedRouteId && !selectedItem()) {
    selectedRouteId = null;
    historyLayer?.clearLayers();
  }
  renderSelectedSummary(selectedItem());
}

async function loadLive({ silent = false, button = null } = {}) {
  if (button) setButtonLoading(button, true, "Atualizando");
  try {
    const data = await api("/tracking/live");
    liveItems = Array.isArray(data) ? data : [];
    renderAll();
    if (selectedRouteId && selectedItem()) {
      loadHistory(selectedRouteId);
    }
    if (!silent) showToast("Rastreamento atualizado.", "success", 2500);
  } catch (error) {
    if (!silent) showToast(`Erro ao carregar rastreamento: ${error.message}`, "error", 6000);
  } finally {
    if (button) setButtonLoading(button, false);
  }
}

function scheduleLiveReload() {
  if (reloadScheduled) return;
  reloadScheduled = true;
  window.setTimeout(async () => {
    reloadScheduled = false;
    await loadLive({ silent: true });
  }, 500);
}

function updateConnectionStatus(state) {
  const element = document.getElementById("trackingConnection");
  element.classList.remove("online", "offline");

  if (state === "online") {
    element.classList.add("online");
    element.innerHTML = '<span class="tracking-connection-dot"></span>Tempo real ativo';
  } else if (state === "offline") {
    element.classList.add("offline");
    element.innerHTML = '<span class="tracking-connection-dot"></span>Reconectando';
  } else {
    element.innerHTML = '<span class="tracking-connection-dot"></span>Conectando';
  }
}

function clearWebSocketTimers() {
  if (websocketRetryTimer) window.clearTimeout(websocketRetryTimer);
  if (websocketPingTimer) window.clearInterval(websocketPingTimer);
  websocketRetryTimer = null;
  websocketPingTimer = null;
}

function connectWebSocket() {
  if (!navigator.onLine) {
    updateConnectionStatus("offline");
    return;
  }

  clearWebSocketTimers();
  updateConnectionStatus("connecting");
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${protocol}//${window.location.host}/api/v1/tracking/ws`;

  // O navegador envia automaticamente o cookie HttpOnly na conexao de mesma origem.
  // Nenhum token fica exposto na URL, no historico ou nos logs do servidor.
  websocket = new WebSocket(url);
  websocket.addEventListener("open", () => {
    updateConnectionStatus("online");
    websocketPingTimer = window.setInterval(() => {
      if (websocket?.readyState === WebSocket.OPEN) websocket.send("ping");
    }, 25000);
  });
  websocket.addEventListener("message", (event) => {
    try {
      const message = JSON.parse(event.data);
      if (message.type === "tracking.position") scheduleLiveReload();
    } catch {
      // Ignora mensagens sem JSON; o polling continua como contingencia.
    }
  });
  websocket.addEventListener("close", () => {
    updateConnectionStatus("offline");
    clearWebSocketTimers();
    websocketRetryTimer = window.setTimeout(connectWebSocket, 5000);
  });
  websocket.addEventListener("error", () => {
    updateConnectionStatus("offline");
    websocket.close();
  });
}

function bindEvents() {
  document.getElementById("refreshTracking").addEventListener("click", (event) =>
    loadLive({ button: event.currentTarget })
  );
  document.getElementById("fitTrackingMap").addEventListener("click", fitAllMarkers);
  document.getElementById("trackingSearch").addEventListener("input", () => {
    renderDrivers();
  });
  document.getElementById("trackingSignalFilter").addEventListener("change", () => {
    renderDrivers();
  });
  document.getElementById("trackingDriversList").addEventListener("click", (event) => {
    const card = event.target.closest("[data-tracking-route]");
    if (card) selectRoute(Number(card.dataset.trackingRoute));
  });

  window.addEventListener("online", () => {
    connectWebSocket();
    loadLive({ silent: true });
  });
  window.addEventListener("offline", () => updateConnectionStatus("offline"));
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) loadLive({ silent: true });
  });
}

async function initializeTracking() {
  try {
    await initLayout("tracking", ["administrador", "operador"]);
  } catch {
    return;
  }

  initializeMap();
  bindEvents();
  await loadLive({ silent: true });
  const requestedRoute = Number(new URLSearchParams(window.location.search).get("route"));
  if (requestedRoute && liveItems.some((item) => item.route_id === requestedRoute)) {
    selectRoute(requestedRoute);
  }
  connectWebSocket();
  refreshTimer = window.setInterval(() => {
    if (!document.hidden && navigator.onLine) loadLive({ silent: true });
  }, REFRESH_INTERVAL_MS);
}

window.addEventListener("beforeunload", () => {
  if (refreshTimer) window.clearInterval(refreshTimer);
  clearWebSocketTimers();
  if (websocket?.readyState === WebSocket.OPEN) websocket.close();
});

initializeTracking();
