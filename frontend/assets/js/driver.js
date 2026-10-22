import { api, clearSession, logout as logoutSession } from "./api.js";
import { badgeClass, escapeHtml, formatNumber, statusLabel } from "./format.js";
import { requireAuth } from "./layout.js";
import { setButtonLoading, showToast } from "./ui.js";

const TERMINAL_DELIVERY_STATUSES = new Set(["entregue", "devolvida", "cancelada"]);
const ACTIVE_ROUTE_STATUSES = new Set(["aberta", "em_andamento"]);
const TRACKING_MIN_INTERVAL_MS = 20000;
const TRACKING_HEARTBEAT_MS = 60000;
const TRACKING_MIN_DISTANCE_M = 25;

let currentUser = null;
let routes = [];
let selectedRouteId = null;
let loadingData = false;
let operationInProgress = false;
let refreshTimer = null;
let geolocationWatchId = null;
let trackingHeartbeatTimer = null;
let trackingState = "idle";
let latestGeolocation = null;
let pendingGeolocation = null;
let trackingLastSentAt = 0;
let trackingLastSentPosition = null;
let trackingSending = false;

function activeTrackingRoute() {
  return routes.find((route) => route.status === "em_andamento") || null;
}

function metersBetween(left, right) {
  if (!left || !right) return Number.POSITIVE_INFINITY;
  const toRadians = (value) => (value * Math.PI) / 180;
  const earthRadius = 6371000;
  const lat1 = toRadians(left.latitude);
  const lat2 = toRadians(right.latitude);
  const deltaLat = toRadians(right.latitude - left.latitude);
  const deltaLng = toRadians(right.longitude - left.longitude);
  const a =
    Math.sin(deltaLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLng / 2) ** 2;
  return earthRadius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function formatTrackingTime(value) {
  if (!value) return "Nenhuma posição enviada";
  return `Último envio às ${new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value))}`;
}

function trackingCopy() {
  const copies = {
    idle: "O GPS será ativado automaticamente quando a rota iniciar.",
    waiting: "Aguardando autorização e sinal do GPS do aparelho.",
    active: "Localização compartilhada com a operação durante esta viagem.",
    warning: "O GPS está ativo, mas a última posição ainda não foi enviada.",
    offline: "Sem internet. A posição mais recente será enviada quando a conexão voltar.",
    denied: "Permissão de localização negada. Libere o GPS nas configurações do navegador.",
    unavailable: "Não foi possível obter a localização. Verifique se o GPS está ligado.",
    insecure: "No celular, o rastreamento exige acesso por HTTPS.",
    unsupported: "Este navegador não oferece suporte à localização GPS.",
    error: "Não foi possível iniciar o rastreamento. Tente novamente.",
  };
  return copies[trackingState] || copies.idle;
}

function updateTrackingUi(route = chooseRoute()) {
  const panel = document.getElementById("driverTrackingPanel");
  const message = document.getElementById("driverTrackingMessage");
  const lastSent = document.getElementById("driverTrackingLastSent");
  const button = document.getElementById("driverTrackingButton");
  const header = document.getElementById("gpsHeaderStatus");
  if (!panel || !message || !lastSent || !button || !header) return;

  panel.classList.remove("active", "warning", "error");
  header.classList.remove("active", "warning", "error", "offline");

  if (!route) {
    panel.hidden = true;
    header.innerHTML = '<span class="network-dot"></span>GPS';
    button.disabled = true;
    return;
  }

  panel.hidden = false;
  if (route.status !== "em_andamento") {
    message.textContent = "O GPS será ativado automaticamente quando a rota iniciar.";
    lastSent.textContent = "Rota ainda não iniciada";
    button.disabled = true;
    button.textContent = "Aguardando início";
    header.innerHTML = '<span class="network-dot"></span>GPS';
    return;
  }

  message.textContent = trackingCopy();
  lastSent.textContent = formatTrackingTime(trackingLastSentAt || null);

  if (trackingState === "active") {
    panel.classList.add("active");
    header.classList.add("active");
    header.innerHTML = '<span class="network-dot"></span>GPS ativo';
    button.disabled = true;
    button.textContent = "GPS ativo";
  } else if (trackingState === "waiting") {
    panel.classList.add("warning");
    header.classList.add("warning");
    header.innerHTML = '<span class="network-dot"></span>GPS...';
    button.disabled = true;
    button.textContent = "Ativando GPS";
  } else if (trackingState === "offline" || trackingState === "warning") {
    panel.classList.add("warning");
    header.classList.add(trackingState === "offline" ? "offline" : "warning");
    header.innerHTML = `<span class="network-dot"></span>${trackingState === "offline" ? "Sem envio" : "GPS"}`;
    button.disabled = false;
    button.textContent = "Tentar enviar";
  } else {
    panel.classList.add("error");
    header.classList.add("error");
    header.innerHTML = '<span class="network-dot"></span>GPS inativo';
    button.disabled = ["insecure", "unsupported"].includes(trackingState);
    button.textContent = trackingState === "insecure" ? "HTTPS necessário" : "Ativar GPS";
  }
}

function stopTracking({ resetState = true } = {}) {
  if (geolocationWatchId != null && navigator.geolocation) {
    navigator.geolocation.clearWatch(geolocationWatchId);
  }
  if (trackingHeartbeatTimer) window.clearInterval(trackingHeartbeatTimer);
  geolocationWatchId = null;
  trackingHeartbeatTimer = null;
  latestGeolocation = null;
  pendingGeolocation = null;
  trackingSending = false;
  if (resetState) trackingState = "idle";
  updateTrackingUi();
}

function shouldSendPosition(position, force = false) {
  if (force || !trackingLastSentAt || !trackingLastSentPosition) return true;
  const elapsed = Date.now() - trackingLastSentAt;
  const current = {
    latitude: Number(position.coords.latitude),
    longitude: Number(position.coords.longitude),
  };
  return (
    elapsed >= TRACKING_HEARTBEAT_MS ||
    (elapsed >= TRACKING_MIN_INTERVAL_MS &&
      metersBetween(trackingLastSentPosition, current) >= TRACKING_MIN_DISTANCE_M)
  );
}

async function sendTrackingPosition(position, { force = false } = {}) {
  const route = activeTrackingRoute();
  if (!route || !position || trackingSending) return;

  if (!navigator.onLine) {
    pendingGeolocation = position;
    trackingState = "offline";
    updateTrackingUi(route);
    return;
  }
  if (!shouldSendPosition(position, force)) return;

  const latitude = Number(position.coords.latitude);
  const longitude = Number(position.coords.longitude);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return;

  trackingSending = true;
  try {
    await api("/tracking/positions", {
      method: "POST",
      body: {
        route_id: route.id,
        latitude,
        longitude,
        accuracy_m: Number.isFinite(Number(position.coords.accuracy))
          ? Number(position.coords.accuracy)
          : null,
        speed_kmh:
          position.coords.speed != null && Number.isFinite(Number(position.coords.speed))
            ? Math.max(0, Number(position.coords.speed) * 3.6)
            : null,
        heading:
          position.coords.heading != null && Number.isFinite(Number(position.coords.heading))
            ? Number(position.coords.heading)
            : null,
        altitude_m:
          position.coords.altitude != null && Number.isFinite(Number(position.coords.altitude))
            ? Number(position.coords.altitude)
            : null,
        captured_at: new Date(position.timestamp || Date.now()).toISOString(),
        source: "mobile_web",
      },
    });

    trackingLastSentAt = Date.now();
    trackingLastSentPosition = { latitude, longitude };
    pendingGeolocation = null;
    trackingState = "active";
    updateTrackingUi(route);
  } catch (error) {
    if ([403, 409].includes(error.status)) {
      stopTracking({ resetState: false });
      trackingState = "error";
      showToast(error.message, "error", 6500);
    } else {
      pendingGeolocation = position;
      trackingState = navigator.onLine ? "warning" : "offline";
    }
    updateTrackingUi(route);
  } finally {
    trackingSending = false;
  }
}

function handleGeolocationSuccess(position) {
  latestGeolocation = position;
  trackingState = navigator.onLine ? "active" : "offline";
  updateTrackingUi(activeTrackingRoute());
  sendTrackingPosition(position);
}

function handleGeolocationError(error, { silent = false } = {}) {
  if (error?.code === 1) trackingState = "denied";
  else if (error?.code === 2) trackingState = "unavailable";
  else if (error?.code === 3) trackingState = "warning";
  else trackingState = "error";

  if ([1, 2].includes(error?.code)) {
    if (geolocationWatchId != null && navigator.geolocation) {
      navigator.geolocation.clearWatch(geolocationWatchId);
    }
    geolocationWatchId = null;
    if (trackingHeartbeatTimer) window.clearInterval(trackingHeartbeatTimer);
    trackingHeartbeatTimer = null;
  }

  updateTrackingUi(activeTrackingRoute());
  if (!silent && error?.code !== 3) {
    showToast(trackingCopy(), "warning", 6500);
  }
}

function startTracking({ silent = false } = {}) {
  const route = activeTrackingRoute();
  if (!route) {
    stopTracking();
    return;
  }

  if (!("geolocation" in navigator)) {
    trackingState = "unsupported";
    updateTrackingUi(route);
    return;
  }

  if (!window.isSecureContext) {
    trackingState = "insecure";
    updateTrackingUi(route);
    if (!silent) {
      showToast("Para rastrear pelo celular, abra o TMS por HTTPS.", "warning", 7000);
    }
    return;
  }

  if (geolocationWatchId != null) {
    if (latestGeolocation) sendTrackingPosition(latestGeolocation, { force: true });
    return;
  }

  trackingState = "waiting";
  updateTrackingUi(route);
  geolocationWatchId = navigator.geolocation.watchPosition(
    handleGeolocationSuccess,
    (error) => handleGeolocationError(error, { silent }),
    {
      enableHighAccuracy: true,
      timeout: 25000,
      maximumAge: 10000,
    }
  );

  trackingHeartbeatTimer = window.setInterval(() => {
    if (latestGeolocation) {
      sendTrackingPosition(latestGeolocation, { force: true });
    }
  }, TRACKING_HEARTBEAT_MS);
}

function syncTrackingWithRoute({ silent = true } = {}) {
  const route = activeTrackingRoute();
  if (!route) {
    if (geolocationWatchId != null || trackingHeartbeatTimer) stopTracking();
    else updateTrackingUi(chooseRoute());
    return;
  }
  updateTrackingUi(route);
  startTracking({ silent });
}

function plural(value, singular, pluralForm = `${singular}s`) {
  return `${value} ${value === 1 ? singular : pluralForm}`;
}

function formatScheduledDate(value) {
  if (!value) return "Sem data prevista";
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (match) {
    const [, year, month, day] = match;
    return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" }).format(
      new Date(Number(year), Number(month) - 1, Number(day))
    );
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" }).format(date);
}

function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function sortedDeliveries(route) {
  return [...(route?.deliveries || [])].sort((left, right) => {
    const leftSequence = Number(left.sequence ?? Number.MAX_SAFE_INTEGER);
    const rightSequence = Number(right.sequence ?? Number.MAX_SAFE_INTEGER);
    return leftSequence - rightSequence || Number(left.id) - Number(right.id);
  });
}

function activeRoutes() {
  return routes.filter((route) => ACTIVE_ROUTE_STATUSES.has(route.status));
}

function chooseRoute() {
  const candidates = activeRoutes();
  if (!candidates.length) return null;

  const inProgress = candidates.find((route) => route.status === "em_andamento");
  if (inProgress) return inProgress;

  if (selectedRouteId != null) {
    const selected = candidates.find((route) => route.id === Number(selectedRouteId));
    if (selected) return selected;
  }

  return candidates.find((route) => route.status === "aberta") || candidates[0];
}

function deliveryProgress(route) {
  const deliveries = sortedDeliveries(route);
  const terminal = deliveries.filter((delivery) =>
    TERMINAL_DELIVERY_STATUSES.has(delivery.status)
  );
  const delivered = deliveries.filter((delivery) => delivery.status === "entregue");
  const returned = deliveries.filter((delivery) => delivery.status === "devolvida");
  const pending = deliveries.filter(
    (delivery) => !TERMINAL_DELIVERY_STATUSES.has(delivery.status)
  );

  return {
    total: deliveries.length,
    terminal: terminal.length,
    delivered: delivered.length,
    returned: returned.length,
    pending: pending.length,
    percent: deliveries.length
      ? Math.round((terminal.length / deliveries.length) * 100)
      : 0,
  };
}

function fullAddress(delivery) {
  const cityState = [delivery.city, delivery.state].filter(Boolean).join("/");
  return [delivery.address, cityState, delivery.postal_code]
    .filter(Boolean)
    .join(" • ");
}

function navigationUrl(delivery) {
  const latitude = Number(delivery.latitude);
  const longitude = Number(delivery.longitude);
  const destination =
    Number.isFinite(latitude) && Number.isFinite(longitude)
      ? `${latitude},${longitude}`
      : [delivery.address, delivery.city, delivery.state, delivery.postal_code, "Brasil"]
          .filter(Boolean)
          .join(", ");

  return `https://www.google.com/maps/dir/?api=1&travelmode=driving&destination=${encodeURIComponent(
    destination
  )}`;
}

function currentNextStop(route) {
  return sortedDeliveries(route).find(
    (delivery) => !TERMINAL_DELIVERY_STATUSES.has(delivery.status)
  );
}

function updateHeader() {
  document.getElementById("driverName").textContent = currentUser?.name || "Motorista";
}

function renderRouteHero(route) {
  const progress = deliveryProgress(route);
  const vehicleDescription = route.vehicle
    ? `${route.vehicle.plate} • ${route.vehicle.brand || ""} ${route.vehicle.model || ""}`.trim()
    : "Veículo não informado";

  document.getElementById("routeStatus").textContent = statusLabel(route.status);
  document.getElementById("routeSchedule").textContent = formatScheduledDate(
    route.scheduled_date
  );
  document.getElementById("routeTitle").textContent = route.name;
  document.getElementById("routeVehicle").textContent = vehicleDescription;
  document.getElementById("routeProgressText").textContent =
    `${progress.terminal} de ${progress.total} paradas finalizadas`;
  document.getElementById("routeProgressPercent").textContent = `${progress.percent}%`;
  document.getElementById("routeProgressBar").style.width = `${progress.percent}%`;
  document.getElementById("routeStopsMetric").textContent = progress.total;
  document.getElementById("routeDistanceMetric").textContent =
    route.distance_km == null ? "—" : `${formatNumber(route.distance_km, 1)} km`;
  document.getElementById("routeStartMetric").textContent = formatTime(route.started_at);
}

function renderRouteAction(route) {
  const panel = document.getElementById("routeActionPanel");
  const progress = deliveryProgress(route);

  if (route.status === "aberta") {
    panel.innerHTML = `
      <div class="driver-action-copy">
        <strong>Rota pronta para iniciar</strong>
        <span>Confira o veículo e as paradas. Ao iniciar, as entregas passam para Em rota.</span>
      </div>
      <button class="driver-primary-button" type="button" data-route-status="em_andamento" data-route-id="${route.id}">
        Iniciar rota
      </button>
    `;
    return;
  }

  if (route.status === "em_andamento" && progress.pending > 0) {
    panel.innerHTML = `
      <div class="driver-action-copy">
        <strong>Viagem em andamento</strong>
        <span>Finalize ${plural(progress.pending, "parada")} antes de concluir a rota.</span>
      </div>
      <div class="driver-inline-alert">
        ${plural(progress.delivered, "entrega confirmada", "entregas confirmadas")} •
        ${plural(progress.returned, "devolução", "devoluções")}
      </div>
      <button class="driver-primary-button" type="button" disabled>
        Faltam ${plural(progress.pending, "parada")}
      </button>
    `;
    return;
  }

  if (route.status === "em_andamento") {
    panel.innerHTML = `
      <div class="driver-action-copy">
        <strong>Todas as paradas foram finalizadas</strong>
        <span>Revise as confirmações e encerre a viagem.</span>
      </div>
      <div class="driver-inline-alert success">
        Rota pronta para conclusão.
      </div>
      <button class="driver-success-button" type="button" data-route-status="concluida" data-route-id="${route.id}">
        Concluir rota
      </button>
    `;
    return;
  }

  panel.innerHTML = "";
}

function renderNextStop(route) {
  const section = document.getElementById("nextStopSection");
  const nextStop = currentNextStop(route);

  if (!nextStop) {
    section.hidden = true;
    return;
  }

  section.hidden = false;
  document.getElementById("nextStopCustomer").textContent = nextStop.customer_name;
  document.getElementById("nextStopSequence").textContent = nextStop.sequence || "—";
  document.getElementById("nextStopAddress").textContent = fullAddress(nextStop);
  document.getElementById("nextStopMapLink").href = navigationUrl(nextStop);
  document.getElementById("nextStopDetailsButton").dataset.stopId = nextStop.id;
}

function stopStatusClass(status) {
  return badgeClass(status);
}

function renderStopCard(delivery, route, nextStopId) {
  const terminal = TERMINAL_DELIVERY_STATUSES.has(delivery.status);
  const isDelivered = delivery.status === "entregue";
  const isReturned = delivery.status === "devolvida";
  const isNext = delivery.id === nextStopId;
  const cardClasses = [
    "driver-stop-card",
    terminal ? "is-terminal" : "",
    isDelivered ? "is-delivered" : "",
    isReturned ? "is-returned" : "",
    isNext ? "is-next" : "",
  ]
    .filter(Boolean)
    .join(" ");

  let actions = `
    <div class="driver-stop-actions">
      <a class="driver-secondary-button" href="${escapeHtml(
        navigationUrl(delivery)
      )}" target="_blank" rel="noopener noreferrer" aria-label="Abrir navegação para a parada">
        Mapa
      </a>
  `;

  if (route.status === "em_andamento" && !terminal) {
    actions += `
      <button class="driver-success-button" type="button" data-delivery-status="entregue" data-delivery-id="${delivery.id}">
        Entregue
      </button>
      <button class="driver-return-button" type="button" data-delivery-status="devolvida" data-delivery-id="${delivery.id}">
        Devolvida
      </button>
    `;
  } else if (route.status === "aberta" && !terminal) {
    actions += `
      <button class="driver-primary-button" type="button" disabled>
        Inicie a rota para confirmar
      </button>
    `;
  }

  actions += "</div>";

  let note = "";
  if (isDelivered) {
    note = `<p class="driver-stop-note">Entrega confirmada${
      delivery.delivered_at ? ` em ${escapeHtml(formatDateTime(delivery.delivered_at))}` : ""
    }.</p>`;
  } else if (isReturned) {
    note = '<p class="driver-stop-note">Entrega registrada como devolvida.</p>';
  } else if (delivery.status === "cancelada") {
    note = '<p class="driver-stop-note">Esta entrega foi cancelada.</p>';
  }

  const weight = delivery.weight_kg == null ? "—" : `${formatNumber(delivery.weight_kg, 1)} kg`;
  const volume = delivery.volume_m3 == null ? "—" : `${formatNumber(delivery.volume_m3, 2)} m³`;
  const document = delivery.customer_document || "—";

  return `
    <article id="stop-${delivery.id}" class="${cardClasses}">
      <div class="driver-stop-heading">
        <span class="driver-stop-number">${escapeHtml(delivery.sequence || "—")}</span>
        <div class="driver-stop-title">
          <small>NF ${escapeHtml(delivery.invoice_number)}</small>
          <strong>${escapeHtml(delivery.customer_name)}</strong>
        </div>
        <span class="driver-stop-status ${escapeHtml(stopStatusClass(delivery.status))}">
          ${escapeHtml(statusLabel(delivery.status))}
        </span>
      </div>

      <p class="driver-stop-address">${escapeHtml(fullAddress(delivery))}</p>

      <div class="driver-stop-meta">
        <div><small>Peso</small><strong>${escapeHtml(weight)}</strong></div>
        <div><small>Volume</small><strong>${escapeHtml(volume)}</strong></div>
        <div><small>Documento</small><strong>${escapeHtml(document)}</strong></div>
      </div>

      ${actions}
      ${note}
    </article>
  `;
}

function renderStops(route) {
  const list = document.getElementById("driverStopsList");
  const deliveries = sortedDeliveries(route);
  const progress = deliveryProgress(route);
  const nextStop = currentNextStop(route);

  document.getElementById("pendingStopsCount").textContent =
    `${progress.pending} pendente${progress.pending === 1 ? "" : "s"}`;

  if (!deliveries.length) {
    list.innerHTML = `
      <div class="driver-inline-alert danger">
        Esta rota ainda não possui entregas vinculadas. Fale com a operação.
      </div>
    `;
    return;
  }

  list.innerHTML = deliveries
    .map((delivery) => renderStopCard(delivery, route, nextStop?.id))
    .join("");
}

function renderOtherRoutes(route) {
  const section = document.getElementById("otherRoutesSection");
  const list = document.getElementById("otherRoutesList");
  const others = activeRoutes().filter((item) => item.id !== route.id);

  if (!others.length) {
    section.hidden = true;
    list.innerHTML = "";
    return;
  }

  section.hidden = false;
  list.innerHTML = others
    .map((item) => {
      const progress = deliveryProgress(item);
      return `
        <button class="driver-route-switch-button" type="button" data-select-route="${item.id}">
          <span>
            <strong>${escapeHtml(item.name)}</strong>
            <small>${escapeHtml(item.vehicle?.plate || "Sem veículo")} • ${escapeHtml(
              statusLabel(item.status)
            )} • ${progress.total} paradas</small>
          </span>
          <span>›</span>
        </button>
      `;
    })
    .join("");
}

function renderHistory() {
  const section = document.getElementById("routeHistorySection");
  const list = document.getElementById("routeHistoryList");
  const history = routes
    .filter((route) => ["concluida", "cancelada"].includes(route.status))
    .slice(0, 6);

  if (!history.length) {
    section.hidden = true;
    list.innerHTML = "";
    return;
  }

  section.hidden = false;
  list.innerHTML = history
    .map((route) => {
      const progress = deliveryProgress(route);
      const date = route.completed_at || route.updated_at || route.created_at;
      return `
        <article class="driver-history-row">
          <div>
            <strong>${escapeHtml(route.name)}</strong>
            <small>${escapeHtml(formatDateTime(date))} • ${progress.total} paradas • ${escapeHtml(
              route.vehicle?.plate || "Sem veículo"
            )}</small>
          </div>
          <span class="driver-stop-status ${escapeHtml(stopStatusClass(route.status))}">
            ${escapeHtml(statusLabel(route.status))}
          </span>
        </article>
      `;
    })
    .join("");
}

function render() {
  const route = chooseRoute();
  const loaded = document.getElementById("driverLoaded");
  const empty = document.getElementById("noActiveRoute");
  const content = document.getElementById("activeRouteContent");

  loaded.hidden = false;
  renderHistory();

  if (!route) {
    selectedRouteId = null;
    empty.hidden = false;
    content.hidden = true;
    updateTrackingUi(null);
    return;
  }

  selectedRouteId = route.id;
  empty.hidden = true;
  content.hidden = false;
  renderRouteHero(route);
  renderRouteAction(route);
  updateTrackingUi(route);
  renderNextStop(route);
  renderOtherRoutes(route);
  renderStops(route);
}

function replaceRoute(updatedRoute) {
  const index = routes.findIndex((route) => route.id === updatedRoute.id);
  if (index === -1) routes.unshift(updatedRoute);
  else routes[index] = updatedRoute;
}

function replaceDelivery(updatedDelivery) {
  const route = routes.find((item) => item.id === Number(updatedDelivery.route_id));
  if (!route) return;
  const index = (route.deliveries || []).findIndex(
    (delivery) => delivery.id === updatedDelivery.id
  );
  if (index === -1) route.deliveries.push(updatedDelivery);
  else route.deliveries[index] = updatedDelivery;
}

async function loadDriverData({ button = null, silent = false } = {}) {
  if (loadingData || operationInProgress) return;
  loadingData = true;

  const originalButtonHtml = button?.innerHTML;
  if (button) {
    button.disabled = true;
    button.innerHTML = '<span class="loading-spinner"></span>';
  }

  try {
    const routeItems = await api("/routes");
    routes = Array.isArray(routeItems) ? routeItems : [];

    if (selectedRouteId != null && !routes.some((route) => route.id === selectedRouteId)) {
      selectedRouteId = null;
    }

    render();
    syncTrackingWithRoute({ silent: true });
    if (!silent) showToast("Rota sincronizada.", "success", 2500);
  } catch (error) {
    if (!silent) showToast(`Não foi possível atualizar: ${error.message}`, "error", 6000);
  } finally {
    loadingData = false;
    document.getElementById("driverLoading").hidden = true;
    document.getElementById("driverLoaded").hidden = false;
    if (button) {
      button.disabled = false;
      button.innerHTML = originalButtonHtml || "↻";
    }
  }
}

function routeById(id) {
  return routes.find((route) => route.id === Number(id));
}

async function changeRouteStatus(routeId, status, button) {
  const route = routeById(routeId);
  if (!route || operationInProgress) return;

  const progress = deliveryProgress(route);
  if (status === "concluida" && progress.pending > 0) {
    showToast(`Finalize ${plural(progress.pending, "parada")} antes de concluir.`, "warning", 5000);
    return;
  }

  const confirmation =
    status === "em_andamento"
      ? "Confirma o início desta rota? As entregas passarão para Em rota."
      : "Confirma a conclusão da rota? Esta ação encerrará a viagem.";

  if (!window.confirm(confirmation)) return;

  operationInProgress = true;
  setButtonLoading(button, true, status === "em_andamento" ? "Iniciando" : "Concluindo");

  try {
    const updatedRoute = await api(`/routes/${route.id}/status`, {
      method: "PATCH",
      body: { status },
    });
    replaceRoute(updatedRoute);

    if (status === "concluida") selectedRouteId = null;
    else selectedRouteId = updatedRoute.id;

    render();
    syncTrackingWithRoute({ silent: status !== "em_andamento" });
    showToast(
      status === "em_andamento"
        ? "Rota iniciada. Boa viagem!"
        : "Rota concluída com sucesso.",
      "success",
      5000
    );
  } catch (error) {
    showToast(error.message, "error", 6500);
  } finally {
    operationInProgress = false;
    setButtonLoading(button, false);
    await loadDriverData({ silent: true });
  }
}

async function updateDeliveryStatus(deliveryId, status, button) {
  const route = chooseRoute();
  const delivery = route?.deliveries?.find((item) => item.id === Number(deliveryId));
  if (!route || !delivery || operationInProgress) return;

  if (route.status !== "em_andamento") {
    showToast("Inicie a rota antes de confirmar uma entrega.", "warning", 5000);
    return;
  }

  const actionLabel = status === "entregue" ? "confirmar a entrega" : "registrar a devolução";
  if (!window.confirm(`Deseja ${actionLabel} da NF ${delivery.invoice_number}?`)) return;

  operationInProgress = true;
  setButtonLoading(button, true, status === "entregue" ? "Confirmando" : "Registrando");

  try {
    const updatedDelivery = await api(`/deliveries/${delivery.id}`, {
      method: "PATCH",
      body: { status },
    });
    replaceDelivery(updatedDelivery);
    render();
    showToast(
      status === "entregue" ? "Entrega confirmada." : "Devolução registrada.",
      status === "entregue" ? "success" : "warning",
      4200
    );

    const nextStop = currentNextStop(chooseRoute());
    if (nextStop) {
      window.setTimeout(() => scrollToStop(nextStop.id), 250);
    }
  } catch (error) {
    showToast(error.message, "error", 6500);
  } finally {
    operationInProgress = false;
    setButtonLoading(button, false);
    await loadDriverData({ silent: true });
  }
}

function scrollToStop(stopId) {
  document.getElementById(`stop-${stopId}`)?.scrollIntoView({
    behavior: "smooth",
    block: "center",
  });
}

function updateNetworkStatus() {
  const indicator = document.getElementById("networkStatus");
  const online = navigator.onLine;
  indicator.classList.toggle("offline", !online);
  indicator.innerHTML = `<span class="network-dot"></span>${online ? "Online" : "Offline"}`;
}

async function logout() {
  if (!window.confirm("Deseja sair do aplicativo do motorista?")) return;
  stopTracking();
  try {
    await logoutSession();
  } catch {
    clearSession();
  }
  window.location.replace("/login");
}

function bindEvents() {
  document.getElementById("driverRefreshButton").addEventListener("click", (event) =>
    loadDriverData({ button: event.currentTarget })
  );
  document.getElementById("bottomRefreshButton").addEventListener("click", (event) =>
    loadDriverData({ button: event.currentTarget })
  );
  document.getElementById("emptyRefreshButton").addEventListener("click", (event) =>
    loadDriverData({ button: event.currentTarget })
  );
  document.getElementById("driverLogoutButton").addEventListener("click", logout);
  document.getElementById("driverTrackingButton").addEventListener("click", () => {
    if (pendingGeolocation && navigator.onLine) {
      sendTrackingPosition(pendingGeolocation, { force: true });
    } else {
      startTracking({ silent: false });
    }
  });

  document.getElementById("driverLoaded").addEventListener("click", (event) => {
    const routeButton = event.target.closest("[data-route-status]");
    if (routeButton) {
      changeRouteStatus(
        Number(routeButton.dataset.routeId),
        routeButton.dataset.routeStatus,
        routeButton
      );
      return;
    }

    const deliveryButton = event.target.closest("[data-delivery-status]");
    if (deliveryButton) {
      updateDeliveryStatus(
        Number(deliveryButton.dataset.deliveryId),
        deliveryButton.dataset.deliveryStatus,
        deliveryButton
      );
      return;
    }

    const routeSwitch = event.target.closest("[data-select-route]");
    if (routeSwitch) {
      selectedRouteId = Number(routeSwitch.dataset.selectRoute);
      render();
      document.getElementById("driverTop").scrollIntoView({ behavior: "smooth" });
    }
  });

  document.getElementById("nextStopDetailsButton").addEventListener("click", (event) => {
    const stopId = Number(event.currentTarget.dataset.stopId);
    if (stopId) scrollToStop(stopId);
  });

  document.querySelectorAll("[data-driver-nav]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.driverNav;
      if (target === "route") {
        document.getElementById("driverTop").scrollIntoView({ behavior: "smooth" });
      } else {
        document.getElementById("driverStops")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    });
  });

  window.addEventListener("online", () => {
    updateNetworkStatus();
    showToast("Conexão restabelecida. Sincronizando...", "success", 3000);
    if (pendingGeolocation) sendTrackingPosition(pendingGeolocation, { force: true });
    loadDriverData({ silent: true });
  });
  window.addEventListener("offline", () => {
    updateNetworkStatus();
    if (activeTrackingRoute()) {
      trackingState = "offline";
      updateTrackingUi(activeTrackingRoute());
    }
    showToast("Sem conexão. A última posição será enviada quando a internet voltar.", "warning", 6000);
  });

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) loadDriverData({ silent: true });
  });
}

async function initializeDriverApp() {
  try {
    currentUser = await requireAuth(["motorista"]);
  } catch {
    return;
  }

  updateHeader();
  updateNetworkStatus();
  bindEvents();
  await loadDriverData({ silent: true });
  syncTrackingWithRoute({ silent: true });

  refreshTimer = window.setInterval(() => {
    if (!document.hidden && navigator.onLine) {
      loadDriverData({ silent: true });
    }
  }, 30000);
}

window.addEventListener("beforeunload", () => {
  if (refreshTimer) window.clearInterval(refreshTimer);
  stopTracking();
});

initializeDriverApp();
