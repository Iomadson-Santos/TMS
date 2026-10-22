import { api } from "./api.js";
import { badgeClass, escapeHtml, formatDate, formatNumber, statusLabel } from "./format.js";
import { initLayout } from "./layout.js";
import { bindModalDismiss, closeModal, openModal, setButtonLoading, showToast } from "./ui.js";

let routes = [];
let vehicles = [];
let drivers = [];
let availableDeliveries = [];
let currentUser = null;
let selectedDeliveryIds = new Set();

function canManage() {
  return Boolean(currentUser && ["administrador", "operador"].includes(currentUser.role));
}

function filteredRoutes() {
  const search = document.getElementById("routeSearch").value.trim().toLowerCase();
  const status = document.getElementById("routeStatusFilter").value;
  return routes.filter((item) => {
    const text = `${item.name} ${item.vehicle?.plate || ""} ${item.driver?.name || ""}`.toLowerCase();
    return (!search || text.includes(search)) && (!status || item.status === status);
  });
}

function startedLabel(item) {
  return item.started_at
    ? `Iniciada em ${formatDate(item.started_at, true)}`
    : "Rota iniciada";
}

function routeStartBlock(item) {
  if (item.status !== "aberta") return null;
  if (!item.driver_id) return "Atribua um motorista antes de iniciar";

  const driverRoute = routes.find(
    (route) =>
      route.id !== item.id &&
      route.status === "em_andamento" &&
      route.driver_id === item.driver_id
  );
  if (driverRoute) {
    return `Motorista ja esta na rota #${driverRoute.id} (${driverRoute.name})`;
  }

  const vehicleRoute = routes.find(
    (route) =>
      route.id !== item.id &&
      route.status === "em_andamento" &&
      route.vehicle_id === item.vehicle_id
  );
  if (vehicleRoute) {
    return `Veiculo ja esta na rota #${vehicleRoute.id} (${vehicleRoute.name})`;
  }
  return null;
}

function routeActions(item) {
  const actions = [
    `<button class="btn btn-light btn-sm" data-action="details" data-id="${item.id}">Detalhes</button>`,
  ];
  const ownsRoute = currentUser.role !== "motorista" || item.driver_id === currentUser.id;

  if (ownsRoute && item.status === "aberta") {
    const blockedReason = routeStartBlock(item);
    actions.push(
      blockedReason
        ? `<button class="btn btn-light btn-sm" type="button" disabled title="${escapeHtml(
            blockedReason
          )}">Inicio bloqueado</button>`
        : `<button class="btn btn-success btn-sm" data-action="status" data-status="em_andamento" data-id="${item.id}">Iniciar</button>`
    );
    if (canManage()) {
      actions.push(
        `<button class="btn btn-light btn-sm" data-action="optimize" data-id="${item.id}">Otimizar</button>`
      );
      actions.push(
        `<button class="btn btn-warning btn-sm" data-action="status" data-status="cancelada" data-id="${item.id}">Cancelar</button>`
      );
    }
  }

  if (ownsRoute && item.status === "em_andamento") {
    actions.push(
      `<button class="btn btn-light btn-sm" type="button" disabled title="${escapeHtml(startedLabel(item))}">✓ Iniciada</button>`
    );
    if (canManage()) {
      actions.push(
        `<a class="btn btn-light btn-sm" href="/tracking?route=${item.id}">Rastrear</a>`
      );
    }
    actions.push(
      `<button class="btn btn-success btn-sm" data-action="status" data-status="concluida" data-id="${item.id}">Concluir</button>`
    );
    if (canManage()) {
      actions.push(
        `<button class="btn btn-warning btn-sm" data-action="status" data-status="cancelada" data-id="${item.id}">Cancelar</button>`
      );
    }
  }

  if (item.status === "concluida") {
    actions.push('<button class="btn btn-light btn-sm" type="button" disabled>✓ Concluída</button>');
  }

  if (item.status === "cancelada") {
    actions.push('<button class="btn btn-light btn-sm" type="button" disabled>Cancelada</button>');
  }

  if (
    currentUser.role === "administrador" &&
    ["aberta", "cancelada"].includes(item.status) &&
    !item.started_at
  ) {
    actions.push(
      `<button class="btn btn-danger btn-sm" data-action="delete" data-id="${item.id}">Excluir</button>`
    );
  }

  return actions.join("");
}

function renderRoutes() {
  const body = document.getElementById("routesBody");
  const rows = filteredRoutes();

  document.getElementById("routeTotal").textContent = routes.length;
  document.getElementById("routeOpen").textContent = routes.filter(
    (item) => item.status === "aberta"
  ).length;
  document.getElementById("routeProgress").textContent = routes.filter(
    (item) => item.status === "em_andamento"
  ).length;
  document.getElementById("routeDone").textContent = routes.filter(
    (item) => item.status === "concluida"
  ).length;

  if (!rows.length) {
    body.innerHTML =
      '<tr><td colspan="9" class="empty-state"><span class="empty-icon">⌁</span>Nenhuma rota encontrada.</td></tr>';
    return;
  }

  body.innerHTML = rows
    .map(
      (item) => `
        <tr>
          <td>#${item.id}</td>
          <td><strong>${escapeHtml(item.name)}</strong><br /><span class="muted small">${escapeHtml(formatDate(item.scheduled_date))}</span></td>
          <td>${escapeHtml(item.vehicle?.plate || "—")}<br /><span class="muted small">${escapeHtml(item.vehicle?.model || "")}</span></td>
          <td>${escapeHtml(item.driver?.name || "Não informado")}</td>
          <td>${item.deliveries?.length || 0}</td>
          <td>${item.distance_km == null ? "—" : `${formatNumber(item.distance_km, 2)} km`}</td>
          <td><span class="badge ${badgeClass(item.status)}">${escapeHtml(statusLabel(item.status))}</span></td>
          <td>${escapeHtml(formatDate(item.created_at, true))}</td>
          <td><div class="row-actions">${routeActions(item)}</div></td>
        </tr>
      `
    )
    .join("");
}

function renderVehicleOptions() {
  const select = document.getElementById("routeVehicle");
  const currentValue = select.value;
  const eligible = vehicles.filter((item) => item.status === "disponivel");
  select.innerHTML =
    '<option value="">Selecione</option>' +
    eligible
      .map(
        (item) =>
          `<option value="${item.id}">${escapeHtml(item.plate)} — ${escapeHtml(item.model)}</option>`
      )
      .join("");

  if ([...select.options].some((option) => option.value === currentValue)) {
    select.value = currentValue;
  }
}

function renderDriverOptions() {
  const select = document.getElementById("routeDriver");
  const currentValue = select.value;
  select.innerHTML =
    '<option value="">Não informado</option>' +
    drivers
      .filter((item) => item.is_active !== false)
      .map((item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`)
      .join("");

  if ([...select.options].some((option) => option.value === currentValue)) {
    select.value = currentValue;
  }
}

function filteredAvailableDeliveries() {
  const search = document.getElementById("routeDeliverySearch").value.trim().toLowerCase();
  return availableDeliveries.filter((item) => {
    const text = `${item.invoice_number} ${item.customer_name} ${item.city} ${item.state} ${item.address}`.toLowerCase();
    return !search || text.includes(search);
  });
}

function updateSelectedCounter() {
  document.getElementById("selectedDeliveryCounter").textContent =
    `${selectedDeliveryIds.size} selecionada${selectedDeliveryIds.size === 1 ? "" : "s"}`;
}

function renderDeliveryPicker() {
  const list = document.getElementById("routeDeliveryList");
  const items = filteredAvailableDeliveries();
  if (!items.length) {
    list.innerHTML = '<div class="empty-state">Nenhuma entrega disponível.</div>';
    updateSelectedCounter();
    return;
  }

  const order = new Map(
    [...selectedDeliveryIds].map((id, index) => [Number(id), index + 1])
  );
  list.innerHTML = items
    .map(
      (item) => `
      <label class="delivery-option">
        <input type="checkbox" data-delivery-id="${item.id}" ${selectedDeliveryIds.has(item.id) ? "checked" : ""} />
        <span>
          <strong>NF ${escapeHtml(item.invoice_number)} — ${escapeHtml(item.customer_name)}</strong>
          <small>${escapeHtml(`${item.city}/${item.state} • ${item.address}`)}</small>
        </span>
        <span class="badge ${selectedDeliveryIds.has(item.id) ? "info" : ""}">${order.get(item.id) ? `Ordem ${order.get(item.id)}` : statusLabel(item.status)}</span>
      </label>
    `
    )
    .join("");
  updateSelectedCounter();
}

function replaceRoute(updatedRoute) {
  const index = routes.findIndex((item) => item.id === updatedRoute.id);
  if (index === -1) {
    routes.unshift(updatedRoute);
  } else {
    routes[index] = updatedRoute;
  }
  renderRoutes();
}

async function loadRoutesData({ button = null, notify = false, showError = true } = {}) {
  if (button) setButtonLoading(button, true, "Atualizando");
  try {
    // As informações principais são carregadas separadamente dos dados do modal.
    // Assim, uma falha ao consultar motoristas não impede a atualização do status das rotas.
    const [routeItems, vehicleItems] = await Promise.all([
      api("/routes"),
      api("/vehicles"),
    ]);

    routes = routeItems;
    vehicles = vehicleItems;
    renderRoutes();
    renderVehicleOptions();

    if (notify) showToast("Rotas atualizadas.", "success");
    return true;
  } catch (error) {
    if (showError) {
      showToast(`Erro ao carregar rotas: ${error.message}`, "error", 6000);
    }
    return false;
  } finally {
    if (button) setButtonLoading(button, false);
  }
}

async function loadRouteCreationOptions({ showWarnings = true } = {}) {
  if (!canManage()) return;

  const [driverResult, deliveryResult] = await Promise.allSettled([
    api("/users/drivers/options?active=true"),
    api("/deliveries?unassigned=true"),
  ]);

  if (driverResult.status === "fulfilled") {
    drivers = driverResult.value;
  } else {
    drivers = [];
    if (showWarnings) {
      showToast(
        `Não foi possível carregar os motoristas: ${driverResult.reason.message}`,
        "warning",
        6500
      );
    }
  }

  if (deliveryResult.status === "fulfilled") {
    availableDeliveries = deliveryResult.value;
  } else {
    availableDeliveries = [];
    if (showWarnings) {
      showToast(
        `Não foi possível carregar as entregas disponíveis: ${deliveryResult.reason.message}`,
        "warning",
        6500
      );
    }
  }

  renderDriverOptions();
  renderDeliveryPicker();
}

async function openCreateRoute() {
  const button = document.getElementById("newRouteButton");
  setButtonLoading(button, true, "Carregando");
  try {
    document.getElementById("routeForm").reset();
    document.getElementById("routeScheduledDate").value = new Date()
      .toISOString()
      .slice(0, 10);
    document.getElementById("routeDistancePreview").textContent = "";
    selectedDeliveryIds = new Set();

    await loadRouteCreationOptions();
    renderVehicleOptions();
    renderDriverOptions();
    renderDeliveryPicker();
    openModal("routeModal");
  } finally {
    setButtonLoading(button, false);
  }
}

async function optimizeSelection() {
  const ids = [...selectedDeliveryIds];
  if (ids.length < 2) {
    showToast("Selecione ao menos duas entregas.", "warning");
    return;
  }
  try {
    const result = await api("/routes/optimize", {
      method: "POST",
      body: { delivery_ids: ids },
    });
    selectedDeliveryIds = new Set(result.ordered_delivery_ids);
    document.getElementById("routeDistancePreview").textContent =
      `Distância aproximada entre paradas: ${formatNumber(result.distance_km, 2)} km`;
    renderDeliveryPicker();
    if (result.missing_coordinates.length) {
      showToast(
        `${result.missing_coordinates.length} entrega(s) sem coordenadas ficaram no final.`,
        "warning",
        6000
      );
    } else {
      showToast("Ordem otimizada.", "success");
    }
  } catch (error) {
    showToast(error.message, "error", 6000);
  }
}

async function saveRoute(event) {
  event.preventDefault();
  if (!selectedDeliveryIds.size) {
    showToast("Selecione ao menos uma entrega.", "warning");
    return;
  }
  const button = document.getElementById("saveRouteButton");
  setButtonLoading(button, true, "Criando");
  try {
    const driver = document.getElementById("routeDriver").value;
    const createdRoute = await api("/routes", {
      method: "POST",
      body: {
        name: document.getElementById("routeName").value.trim(),
        vehicle_id: Number(document.getElementById("routeVehicle").value),
        driver_id: driver ? Number(driver) : null,
        scheduled_date: document.getElementById("routeScheduledDate").value || null,
        notes: document.getElementById("routeNotes").value.trim() || null,
        delivery_ids: [...selectedDeliveryIds],
      },
    });
    replaceRoute(createdRoute);
    showToast("Rota criada com sucesso.", "success");
    closeModal("routeModal");
    selectedDeliveryIds = new Set();
    await loadRoutesData({ showError: false });
  } catch (error) {
    showToast(error.message, "error", 6000);
  } finally {
    setButtonLoading(button, false);
  }
}

function statusSuccessMessage(status) {
  const messages = {
    em_andamento: "Rota iniciada. O status agora é Em andamento.",
    concluida: "Rota concluída com sucesso.",
    cancelada: "Rota cancelada.",
  };
  return messages[status] || "Status da rota atualizado.";
}

async function changeRouteStatus(id, status, button = null) {
  if (!window.confirm(`Confirma alterar a rota para ${statusLabel(status)}?`)) return;

  const loadingLabel = status === "em_andamento" ? "Iniciando" : "Atualizando";
  setButtonLoading(button, true, loadingLabel);

  try {
    const updatedRoute = await api(`/routes/${id}/status`, {
      method: "PATCH",
      body: { status },
    });

    // Atualiza a linha imediatamente. O botão Iniciar desaparece e passa a mostrar
    // "Iniciada" + "Concluir", mesmo que uma consulta auxiliar falhe depois.
    replaceRoute(updatedRoute);
    showToast(statusSuccessMessage(status), "success", 5500);

    // Sincroniza a lista principal e o veículo sem consultar endpoints auxiliares.
    await loadRoutesData({ showError: false });
  } catch (error) {
    // Em caso de conflito, sincroniza a tela para refletir o status real do servidor.
    await loadRoutesData({ showError: false });
    showToast(error.message, "error", 6000);
  } finally {
    setButtonLoading(button, false);
  }
}

async function optimizeExistingRoute(id, button = null) {
  setButtonLoading(button, true, "Otimizando");
  try {
    const updatedRoute = await api(`/routes/${id}/optimize`, { method: "POST" });
    replaceRoute(updatedRoute);
    showToast("Rota otimizada.", "success");
  } catch (error) {
    showToast(error.message, "error", 6000);
  } finally {
    setButtonLoading(button, false);
  }
}

async function deleteRoute(id, button = null) {
  if (!window.confirm("Confirma a exclusão desta rota?")) return;
  setButtonLoading(button, true, "Excluindo");
  try {
    await api(`/routes/${id}`, { method: "DELETE" });
    routes = routes.filter((item) => item.id !== Number(id));
    renderRoutes();
    showToast("Rota excluída.", "success");
    await loadRoutesData({ showError: false });
  } catch (error) {
    showToast(error.message, "error", 6000);
  } finally {
    setButtonLoading(button, false);
  }
}

function showRouteDetails(id) {
  const item = routes.find((route) => route.id === Number(id));
  if (!item) return;
  const deliveriesHtml = item.deliveries?.length
    ? `<div class="table-wrap"><table class="data-table"><thead><tr><th>Ordem</th><th>NF</th><th>Cliente</th><th>Destino</th><th>Status</th></tr></thead><tbody>${item.deliveries
        .map(
          (delivery) =>
            `<tr><td>${delivery.sequence || "—"}</td><td>${escapeHtml(delivery.invoice_number)}</td><td>${escapeHtml(delivery.customer_name)}</td><td>${escapeHtml(`${delivery.city}/${delivery.state}`)}</td><td><span class="badge ${badgeClass(delivery.status)}">${escapeHtml(statusLabel(delivery.status))}</span></td></tr>`
        )
        .join("")}</tbody></table></div>`
    : '<div class="empty-state">Nenhuma entrega vinculada.</div>';

  document.getElementById("routeDetailsContent").innerHTML = `
    <div class="details-grid">
      <div class="detail-box"><small>Rota</small><strong>${escapeHtml(item.name)}</strong></div>
      <div class="detail-box"><small>Status</small><strong>${escapeHtml(statusLabel(item.status))}</strong></div>
      <div class="detail-box"><small>Data prevista</small><strong>${escapeHtml(formatDate(item.scheduled_date))}</strong></div>
      <div class="detail-box"><small>Veículo</small><strong>${escapeHtml(item.vehicle?.plate || "—")}</strong></div>
      <div class="detail-box"><small>Motorista</small><strong>${escapeHtml(item.driver?.name || "Não informado")}</strong></div>
      <div class="detail-box"><small>Distância estimada</small><strong>${item.distance_km == null ? "—" : `${formatNumber(item.distance_km, 2)} km`}</strong></div>
      <div class="detail-box"><small>Iniciada em</small><strong>${escapeHtml(formatDate(item.started_at, true))}</strong></div>
      <div class="detail-box"><small>Concluída em</small><strong>${escapeHtml(formatDate(item.completed_at, true))}</strong></div>
    </div>
    <div class="detail-box" style="margin-bottom: 18px"><small>Observações</small><strong>${escapeHtml(item.notes || "Sem observações")}</strong></div>
    <h3>Entregas da rota</h3>
    ${deliveriesHtml}
  `;
  openModal("routeDetailsModal");
}

currentUser = await initLayout("routes");
bindModalDismiss();
document.getElementById("newRouteButton").hidden = !canManage();
document.getElementById("newRouteButton").addEventListener("click", openCreateRoute);
document.getElementById("routeForm").addEventListener("submit", saveRoute);
document.getElementById("routeSearch").addEventListener("input", renderRoutes);
document.getElementById("routeStatusFilter").addEventListener("change", renderRoutes);
document.getElementById("routeDeliverySearch").addEventListener("input", renderDeliveryPicker);
document.getElementById("refreshRoutes").addEventListener("click", (event) => {
  loadRoutesData({ button: event.currentTarget, notify: true });
});
document.getElementById("optimizeSelectionButton").addEventListener("click", optimizeSelection);
document.getElementById("selectVisibleDeliveries").addEventListener("click", () => {
  filteredAvailableDeliveries().forEach((item) => selectedDeliveryIds.add(item.id));
  renderDeliveryPicker();
});
document.getElementById("clearSelectedDeliveries").addEventListener("click", () => {
  selectedDeliveryIds.clear();
  renderDeliveryPicker();
});
document.getElementById("routeDeliveryList").addEventListener("change", (event) => {
  const input = event.target.closest("input[data-delivery-id]");
  if (!input) return;
  const id = Number(input.dataset.deliveryId);
  if (input.checked) selectedDeliveryIds.add(id);
  else selectedDeliveryIds.delete(id);
  renderDeliveryPicker();
});
document.getElementById("routesBody").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const { action, id, status } = button.dataset;
  if (action === "details") showRouteDetails(id);
  if (action === "status") changeRouteStatus(id, status, button);
  if (action === "optimize") optimizeExistingRoute(id, button);
  if (action === "delete") deleteRoute(id, button);
});

await loadRoutesData();
