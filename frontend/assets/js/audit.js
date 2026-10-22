import { api } from "./api.js";
import { escapeHtml, formatDate, statusLabel } from "./format.js";
import { initLayout } from "./layout.js";
import { showToast } from "./ui.js";

let logs = [];

function filteredLogs() {
  const entity = document.getElementById("auditEntityFilter").value;
  const action = document.getElementById("auditActionFilter").value;
  return logs.filter((item) => (!entity || item.entity_type === entity) && (!action || item.action === action));
}

function renderAudit() {
  const body = document.getElementById("auditBody");
  const rows = filteredLogs();
  document.getElementById("auditTotal").textContent = logs.length;
  document.getElementById("auditLogins").textContent = logs.filter((item) => item.action === "login").length;
  document.getElementById("auditCreates").textContent = logs.filter((item) => item.action === "create").length;
  document.getElementById("auditChanges").textContent = logs.filter((item) => ["update", "status_change", "optimize", "password_change"].includes(item.action)).length;

  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="8" class="empty-state"><span class="empty-icon">≡</span>Nenhum registro encontrado.</td></tr>';
    return;
  }
  body.innerHTML = rows.map((item) => `
    <tr>
      <td>#${item.id}</td>
      <td>${escapeHtml(formatDate(item.created_at, true))}</td>
      <td>${escapeHtml(item.user?.name || "Sistema")}</td>
      <td>${escapeHtml(statusLabel(item.action))}</td>
      <td>${escapeHtml(item.entity_type)}</td>
      <td>${escapeHtml(item.entity_id || "—")}</td>
      <td><span class="small">${escapeHtml(item.details ? JSON.stringify(item.details) : "—")}</span></td>
      <td>${escapeHtml(item.ip_address || "—")}</td>
    </tr>
  `).join("");
}

async function loadAudit() {
  try {
    logs = await api("/audit?limit=500");
    renderAudit();
  } catch (error) {
    showToast(`Erro ao carregar auditoria: ${error.message}`, "error", 6000);
  }
}

await initLayout("audit", ["administrador"]);
document.getElementById("auditEntityFilter").addEventListener("change", renderAudit);
document.getElementById("auditActionFilter").addEventListener("change", renderAudit);
document.getElementById("refreshAudit").addEventListener("click", loadAudit);
loadAudit();
