import { api } from "./api.js";
import { badgeClass, escapeHtml, formatCurrency, formatNumber, statusLabel } from "./format.js";
import { initLayout } from "./layout.js";
import { bindModalDismiss, closeModal, openModal, setButtonLoading, showToast } from "./ui.js";

let deliveries = [];
let currentUser = null;
let editingId = null;

function filteredDeliveries() {
  const search = document.getElementById("deliverySearch").value.trim().toLowerCase();
  const status = document.getElementById("deliveryStatusFilter").value;
  return deliveries.filter((item) => {
    const text = `${item.invoice_number} ${item.customer_name} ${item.customer_document || ""} ${item.city} ${item.state}`.toLowerCase();
    return (!search || text.includes(search)) && (!status || item.status === status);
  });
}

function renderDeliveries() {
  const body = document.getElementById("deliveriesBody");
  const rows = filteredDeliveries();
  const canManage = ["administrador", "operador"].includes(currentUser.role);
  const canDelete = currentUser.role === "administrador";
  const isDriver = currentUser.role === "motorista";

  document.getElementById("deliveryTotal").textContent = deliveries.length;
  document.getElementById("deliveryPending").textContent = deliveries.filter((item) => ["recebida", "separada", "faturada", "pendente"].includes(item.status)).length;
  document.getElementById("deliveryInRoute").textContent = deliveries.filter((item) => item.status === "em_rota").length;
  document.getElementById("deliveryDone").textContent = deliveries.filter((item) => item.status === "entregue").length;

  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="10" class="empty-state"><span class="empty-icon">▣</span>Nenhuma entrega encontrada.</td></tr>';
    return;
  }

  body.innerHTML = rows
    .map((item) => {
      const driverActions = isDriver && item.status === "em_rota"
        ? `<button class="btn btn-success btn-sm" data-action="status" data-status="entregue" data-id="${item.id}">Entregue</button>
           <button class="btn btn-warning btn-sm" data-action="status" data-status="devolvida" data-id="${item.id}">Devolvida</button>`
        : "";
      return `
        <tr>
          <td>#${item.id}</td>
          <td><strong>${escapeHtml(item.invoice_number)}</strong></td>
          <td>${escapeHtml(item.customer_name)}<br /><span class="muted small">${escapeHtml(item.customer_document || "Documento nao informado")}</span></td>
          <td>${escapeHtml(`${item.city}/${item.state}`)}<br /><span class="muted small">${escapeHtml(item.address)}</span></td>
          <td>${item.weight_kg == null ? "—" : `${formatNumber(item.weight_kg, 2)} kg`}</td>
          <td class="money">${formatCurrency(item.invoice_value)}</td>
          <td class="money">${formatCurrency(item.freight_value)}</td>
          <td>${item.route_id ? `#${item.route_id} / ${item.sequence || "—"}` : "—"}</td>
          <td><span class="badge ${badgeClass(item.status)}">${escapeHtml(statusLabel(item.status))}</span></td>
          <td>
            <div class="row-actions">
              ${canManage ? `<button class="btn btn-light btn-sm" data-action="edit" data-id="${item.id}">Editar</button>` : ""}
              ${driverActions}
              ${canDelete && !item.route_id ? `<button class="btn btn-danger btn-sm" data-action="delete" data-id="${item.id}">Excluir</button>` : ""}
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function loadDeliveries() {
  try {
    deliveries = await api("/deliveries");
    renderDeliveries();
  } catch (error) {
    showToast(`Erro ao carregar entregas: ${error.message}`, "error", 6000);
  }
}

function openCreateDelivery() {
  editingId = null;
  document.getElementById("deliveryModalTitle").textContent = "Nova entrega";
  document.getElementById("deliveryForm").reset();
  document.getElementById("deliveryState").value = "SP";
  document.getElementById("deliveryStatus").value = "pendente";
  openModal("deliveryModal");
}

function openEditDelivery(id) {
  const item = deliveries.find((delivery) => delivery.id === Number(id));
  if (!item) return;
  editingId = item.id;
  document.getElementById("deliveryModalTitle").textContent = "Editar entrega";
  const mapping = {
    deliveryInvoice: item.invoice_number,
    deliveryCustomer: item.customer_name,
    deliveryDocument: item.customer_document || "",
    deliveryAddress: item.address,
    deliveryCity: item.city,
    deliveryState: item.state,
    deliveryPostalCode: item.postal_code || "",
    deliveryLatitude: item.latitude ?? "",
    deliveryLongitude: item.longitude ?? "",
    deliveryWeight: item.weight_kg ?? "",
    deliveryVolume: item.volume_m3 ?? "",
    deliveryInvoiceValue: item.invoice_value ?? "",
    deliveryFreightValue: item.freight_value ?? "",
    deliveryStatus: item.status,
  };
  Object.entries(mapping).forEach(([id, value]) => {
    document.getElementById(id).value = value;
  });
  openModal("deliveryModal");
}

function deliveryPayload() {
  const optionalNumber = (id) => {
    const value = document.getElementById(id).value;
    return value === "" ? null : Number(value);
  };
  return {
    invoice_number: document.getElementById("deliveryInvoice").value.trim(),
    customer_name: document.getElementById("deliveryCustomer").value.trim(),
    customer_document: document.getElementById("deliveryDocument").value.trim() || null,
    address: document.getElementById("deliveryAddress").value.trim(),
    city: document.getElementById("deliveryCity").value.trim(),
    state: document.getElementById("deliveryState").value.trim().toUpperCase(),
    postal_code: document.getElementById("deliveryPostalCode").value.trim() || null,
    latitude: optionalNumber("deliveryLatitude"),
    longitude: optionalNumber("deliveryLongitude"),
    weight_kg: optionalNumber("deliveryWeight"),
    volume_m3: optionalNumber("deliveryVolume"),
    invoice_value: optionalNumber("deliveryInvoiceValue"),
    freight_value: optionalNumber("deliveryFreightValue"),
    status: document.getElementById("deliveryStatus").value,
  };
}

async function saveDelivery(event) {
  event.preventDefault();
  const button = document.getElementById("saveDeliveryButton");
  setButtonLoading(button, true, "Salvando");
  try {
    if (editingId) {
      await api(`/deliveries/${editingId}`, { method: "PATCH", body: deliveryPayload() });
      showToast("Entrega atualizada com sucesso.", "success");
    } else {
      await api("/deliveries", { method: "POST", body: deliveryPayload() });
      showToast("Entrega cadastrada com sucesso.", "success");
    }
    closeModal("deliveryModal");
    await loadDeliveries();
  } catch (error) {
    showToast(error.message, "error", 6000);
  } finally {
    setButtonLoading(button, false);
  }
}

async function changeDeliveryStatus(id, status) {
  if (!window.confirm(`Confirma o status ${statusLabel(status)}?`)) return;
  try {
    await api(`/deliveries/${id}`, { method: "PATCH", body: { status } });
    showToast("Status da entrega atualizado.", "success");
    await loadDeliveries();
  } catch (error) {
    showToast(error.message, "error", 6000);
  }
}

async function deleteDelivery(id) {
  if (!window.confirm("Confirma a exclusao desta entrega?")) return;
  try {
    await api(`/deliveries/${id}`, { method: "DELETE" });
    showToast("Entrega excluida.", "success");
    await loadDeliveries();
  } catch (error) {
    showToast(error.message, "error", 6000);
  }
}

currentUser = await initLayout("deliveries");
bindModalDismiss();
document.getElementById("newDeliveryButton").hidden = !["administrador", "operador"].includes(currentUser.role);
document.getElementById("newDeliveryButton").addEventListener("click", openCreateDelivery);
document.getElementById("deliveryForm").addEventListener("submit", saveDelivery);
document.getElementById("deliverySearch").addEventListener("input", renderDeliveries);
document.getElementById("deliveryStatusFilter").addEventListener("change", renderDeliveries);
document.getElementById("refreshDeliveries").addEventListener("click", loadDeliveries);
document.getElementById("deliveriesBody").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  if (button.dataset.action === "edit") openEditDelivery(button.dataset.id);
  if (button.dataset.action === "delete") deleteDelivery(button.dataset.id);
  if (button.dataset.action === "status") changeDeliveryStatus(button.dataset.id, button.dataset.status);
});
loadDeliveries();
