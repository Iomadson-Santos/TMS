import { api } from "./api.js";
import { badgeClass, escapeHtml, formatCurrency, formatDate, statusLabel } from "./format.js";
import { initLayout } from "./layout.js";
import { showToast } from "./ui.js";

function renderRecentDeliveries(deliveries) {
  const body = document.getElementById("recentDeliveriesBody");
  const rows = deliveries.slice(0, 6);
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="5" class="empty-state">Nenhuma entrega cadastrada.</td></tr>';
    return;
  }

  body.innerHTML = rows
    .map(
      (item) => `
        <tr>
          <td><strong>${escapeHtml(item.invoice_number)}</strong></td>
          <td>${escapeHtml(item.customer_name)}</td>
          <td>${escapeHtml(`${item.city}/${item.state}`)}</td>
          <td><span class="badge ${badgeClass(item.status)}">${escapeHtml(statusLabel(item.status))}</span></td>
          <td>${escapeHtml(formatDate(item.created_at))}</td>
        </tr>
      `
    )
    .join("");
}

function renderRecentRoutes(routes) {
  const body = document.getElementById("recentRoutesBody");
  const rows = routes.slice(0, 6);
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="5" class="empty-state">Nenhuma rota cadastrada.</td></tr>';
    return;
  }

  body.innerHTML = rows
    .map(
      (item) => `
        <tr>
          <td><strong>${escapeHtml(item.name)}</strong></td>
          <td>${escapeHtml(item.vehicle?.plate || "—")}</td>
          <td>${escapeHtml(item.driver?.name || "Nao informado")}</td>
          <td>${item.deliveries?.length || 0}</td>
          <td><span class="badge ${badgeClass(item.status)}">${escapeHtml(statusLabel(item.status))}</span></td>
        </tr>
      `
    )
    .join("");
}

async function loadDashboard() {
  try {
    const [summary, deliveries, routes] = await Promise.all([
      api("/dashboard/summary"),
      api("/deliveries"),
      api("/routes"),
    ]);

    document.getElementById("totalDeliveries").textContent = summary.total_deliveries;
    document.getElementById("pendingDeliveries").textContent = summary.pending_deliveries;
    document.getElementById("inProgressRoutes").textContent = summary.in_progress_routes;
    document.getElementById("availableVehicles").textContent = summary.available_vehicles;
    document.getElementById("invoiceTotal").textContent = formatCurrency(summary.invoice_value_total);
    document.getElementById("freightTotal").textContent = formatCurrency(summary.freight_value_total);
    document.getElementById("deliveredCount").textContent = summary.delivered_deliveries;
    document.getElementById("activeDrivers").textContent = summary.active_drivers;

    const ratio = Number(summary.invoice_value_total)
      ? (Number(summary.freight_value_total) / Number(summary.invoice_value_total)) * 100
      : 0;
    document.getElementById("freightRatio").textContent = `${ratio.toFixed(2)}% do valor faturado`;

    renderRecentDeliveries(deliveries);
    renderRecentRoutes(routes);
  } catch (error) {
    showToast(`Erro ao carregar dashboard: ${error.message}`, "error", 6000);
  }
}

await initLayout("dashboard");
loadDashboard();
document.getElementById("refreshDashboard").addEventListener("click", loadDashboard);
