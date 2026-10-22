import { api } from "./api.js";
import { badgeClass, escapeHtml, formatNumber, statusLabel } from "./format.js";
import { initLayout } from "./layout.js";
import { bindModalDismiss, closeModal, openModal, setButtonLoading, showToast } from "./ui.js";

let vehicles = [];
let currentUser = null;
let editingId = null;

function filteredVehicles() {
  const search = document.getElementById("vehicleSearch").value.trim().toLowerCase();
  const status = document.getElementById("vehicleStatusFilter").value;
  return vehicles.filter((item) => {
    const text = `${item.plate} ${item.brand || ""} ${item.model}`.toLowerCase();
    return (!search || text.includes(search)) && (!status || item.status === status);
  });
}

function renderVehicles() {
  const body = document.getElementById("vehiclesBody");
  const rows = filteredVehicles();
  const canManage = ["administrador", "operador"].includes(currentUser.role);
  const canDelete = currentUser.role === "administrador";

  document.getElementById("vehicleTotal").textContent = vehicles.length;
  document.getElementById("vehicleAvailable").textContent = vehicles.filter((item) => item.status === "disponivel").length;
  document.getElementById("vehicleInRoute").textContent = vehicles.filter((item) => item.status === "em_rota").length;
  document.getElementById("vehicleMaintenance").textContent = vehicles.filter((item) => item.status === "manutencao").length;

  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="9" class="empty-state"><span class="empty-icon">▰</span>Nenhum veiculo encontrado.</td></tr>';
    return;
  }

  body.innerHTML = rows
    .map(
      (item) => `
        <tr>
          <td><strong>${escapeHtml(item.plate)}</strong></td>
          <td>${escapeHtml(item.brand || "—")}</td>
          <td>${escapeHtml(item.model)}</td>
          <td>${escapeHtml(item.year || "—")}</td>
          <td>${item.capacity_kg == null ? "—" : `${formatNumber(item.capacity_kg, 2)} kg`}</td>
          <td>${item.capacity_m3 == null ? "—" : `${formatNumber(item.capacity_m3, 3)} m³`}</td>
          <td>${formatNumber(item.current_km)} km</td>
          <td><span class="badge ${badgeClass(item.status)}">${escapeHtml(statusLabel(item.status))}</span></td>
          <td>
            <div class="row-actions">
              ${canManage ? `<button class="btn btn-light btn-sm" data-action="edit" data-id="${item.id}">Editar</button>` : ""}
              ${canDelete ? `<button class="btn btn-danger btn-sm" data-action="delete" data-id="${item.id}">Excluir</button>` : ""}
            </div>
          </td>
        </tr>
      `
    )
    .join("");
}

async function loadVehicles() {
  try {
    vehicles = await api("/vehicles");
    renderVehicles();
  } catch (error) {
    showToast(`Erro ao carregar veiculos: ${error.message}`, "error", 6000);
  }
}

function openCreateVehicle() {
  editingId = null;
  document.getElementById("vehicleModalTitle").textContent = "Novo veiculo";
  document.getElementById("vehicleForm").reset();
  document.getElementById("vehicleStatus").value = "disponivel";
  document.getElementById("vehicleCurrentKm").value = "0";
  openModal("vehicleModal");
}

function openEditVehicle(id) {
  const item = vehicles.find((vehicle) => vehicle.id === Number(id));
  if (!item) return;
  editingId = item.id;
  document.getElementById("vehicleModalTitle").textContent = "Editar veiculo";
  document.getElementById("vehiclePlate").value = item.plate;
  document.getElementById("vehicleBrand").value = item.brand || "";
  document.getElementById("vehicleModel").value = item.model;
  document.getElementById("vehicleYear").value = item.year || "";
  document.getElementById("vehicleCapacityKg").value = item.capacity_kg ?? "";
  document.getElementById("vehicleCapacityM3").value = item.capacity_m3 ?? "";
  document.getElementById("vehicleCurrentKm").value = item.current_km || 0;
  document.getElementById("vehicleStatus").value = item.status;
  openModal("vehicleModal");
}

function vehiclePayload() {
  const optionalNumber = (id) => {
    const value = document.getElementById(id).value;
    return value === "" ? null : Number(value);
  };
  return {
    plate: document.getElementById("vehiclePlate").value,
    brand: document.getElementById("vehicleBrand").value.trim() || null,
    model: document.getElementById("vehicleModel").value.trim(),
    year: optionalNumber("vehicleYear"),
    capacity_kg: optionalNumber("vehicleCapacityKg"),
    capacity_m3: optionalNumber("vehicleCapacityM3"),
    current_km: Number(document.getElementById("vehicleCurrentKm").value || 0),
    status: document.getElementById("vehicleStatus").value,
  };
}

async function saveVehicle(event) {
  event.preventDefault();
  const button = document.getElementById("saveVehicleButton");
  setButtonLoading(button, true, "Salvando");
  try {
    if (editingId) {
      await api(`/vehicles/${editingId}`, { method: "PATCH", body: vehiclePayload() });
      showToast("Veiculo atualizado com sucesso.", "success");
    } else {
      await api("/vehicles", { method: "POST", body: vehiclePayload() });
      showToast("Veiculo cadastrado com sucesso.", "success");
    }
    closeModal("vehicleModal");
    await loadVehicles();
  } catch (error) {
    showToast(error.message, "error", 6000);
  } finally {
    setButtonLoading(button, false);
  }
}

async function deleteVehicle(id) {
  if (!window.confirm("Confirma a exclusao deste veiculo?")) return;
  try {
    await api(`/vehicles/${id}`, { method: "DELETE" });
    showToast("Veiculo excluido.", "success");
    await loadVehicles();
  } catch (error) {
    showToast(error.message, "error", 6000);
  }
}

currentUser = await initLayout("vehicles");
bindModalDismiss();
document.getElementById("newVehicleButton").hidden = !["administrador", "operador"].includes(currentUser.role);
document.getElementById("newVehicleButton").addEventListener("click", openCreateVehicle);
document.getElementById("vehicleForm").addEventListener("submit", saveVehicle);
document.getElementById("vehicleSearch").addEventListener("input", renderVehicles);
document.getElementById("vehicleStatusFilter").addEventListener("change", renderVehicles);
document.getElementById("refreshVehicles").addEventListener("click", loadVehicles);
document.getElementById("vehiclesBody").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  if (button.dataset.action === "edit") openEditVehicle(button.dataset.id);
  if (button.dataset.action === "delete") deleteVehicle(button.dataset.id);
});
loadVehicles();
