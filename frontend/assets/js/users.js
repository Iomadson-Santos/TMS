import { api } from "./api.js";
import { badgeClass, escapeHtml, formatDate, statusLabel } from "./format.js";
import { initLayout } from "./layout.js";
import { bindModalDismiss, closeModal, openModal, setButtonLoading, showToast } from "./ui.js";

let users = [];
let currentUser = null;
let editingId = null;

function filteredUsers() {
  const search = document.getElementById("userSearch").value.trim().toLowerCase();
  const role = document.getElementById("userRoleFilter").value;
  return users.filter((item) => {
    const text = `${item.name} ${item.email}`.toLowerCase();
    return (!search || text.includes(search)) && (!role || item.role === role);
  });
}

function renderUsers() {
  const body = document.getElementById("usersBody");
  const rows = filteredUsers();
  const isAdmin = currentUser.role === "administrador";

  document.getElementById("userTotal").textContent = users.length;
  document.getElementById("userAdmins").textContent = users.filter((item) => item.role === "administrador" && item.is_active).length;
  document.getElementById("userOperators").textContent = users.filter((item) => item.role === "operador" && item.is_active).length;
  document.getElementById("userDrivers").textContent = users.filter((item) => item.role === "motorista" && item.is_active).length;

  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="7" class="empty-state"><span class="empty-icon">◉</span>Nenhum usuario encontrado.</td></tr>';
    return;
  }

  body.innerHTML = rows
    .map(
      (item) => `
        <tr>
          <td>#${item.id}</td>
          <td><strong>${escapeHtml(item.name)}</strong></td>
          <td>${escapeHtml(item.email)}</td>
          <td><span class="badge ${badgeClass(item.role)}">${escapeHtml(statusLabel(item.role))}</span></td>
          <td>
            <span class="badge ${item.is_active ? "success" : "danger"}">${item.is_active ? "Ativo" : "Inativo"}</span>
            ${item.must_change_password ? '<span class="badge warning">Troca de senha pendente</span>' : ""}
          </td>
          <td>${escapeHtml(formatDate(item.created_at))}</td>
          <td>${isAdmin ? `<button class="btn btn-light btn-sm" data-action="edit" data-id="${item.id}">Editar</button>` : "—"}</td>
        </tr>
      `
    )
    .join("");
}

async function loadUsers() {
  try {
    users = await api("/users");
    renderUsers();
  } catch (error) {
    showToast(`Erro ao carregar usuarios: ${error.message}`, "error", 6000);
  }
}

function openCreateUser() {
  editingId = null;
  document.getElementById("userModalTitle").textContent = "Novo usuario";
  document.getElementById("userForm").reset();
  document.getElementById("userRole").value = "operador";
  document.getElementById("userActive").checked = true;
  document.getElementById("userPassword").required = true;
  document.getElementById("passwordHint").textContent = "Senha temporária. Use 12 ou mais caracteres; o usuário deverá alterá-la no primeiro acesso.";
  openModal("userModal");
}

function openEditUser(id) {
  const item = users.find((user) => user.id === Number(id));
  if (!item) return;
  editingId = item.id;
  document.getElementById("userModalTitle").textContent = "Editar usuario";
  document.getElementById("userName").value = item.name;
  document.getElementById("userEmail").value = item.email;
  document.getElementById("userRole").value = item.role;
  document.getElementById("userActive").checked = item.is_active;
  document.getElementById("userPassword").value = "";
  document.getElementById("userPassword").required = false;
  document.getElementById("passwordHint").textContent = "Deixe em branco para manter a senha atual.";
  openModal("userModal");
}

async function saveUser(event) {
  event.preventDefault();
  const password = document.getElementById("userPassword").value;
  const payload = {
    name: document.getElementById("userName").value.trim(),
    email: document.getElementById("userEmail").value.trim(),
    role: document.getElementById("userRole").value,
    is_active: document.getElementById("userActive").checked,
  };
  if (password) payload.password = password;

  const button = document.getElementById("saveUserButton");
  setButtonLoading(button, true, "Salvando");
  try {
    if (editingId) {
      await api(`/users/${editingId}`, { method: "PATCH", body: payload });
      showToast("Usuario atualizado.", "success");
    } else {
      await api("/users", { method: "POST", body: payload });
      showToast("Usuario criado.", "success");
    }
    closeModal("userModal");
    await loadUsers();
  } catch (error) {
    showToast(error.message, "error", 6000);
  } finally {
    setButtonLoading(button, false);
  }
}

currentUser = await initLayout("users", ["administrador"]);
bindModalDismiss();
document.getElementById("newUserButton").hidden = currentUser.role !== "administrador";
document.getElementById("newUserButton").addEventListener("click", openCreateUser);
document.getElementById("userForm").addEventListener("submit", saveUser);
document.getElementById("userSearch").addEventListener("input", renderUsers);
document.getElementById("userRoleFilter").addEventListener("change", renderUsers);
document.getElementById("refreshUsers").addEventListener("click", loadUsers);
document.getElementById("usersBody").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action='edit']");
  if (button) openEditUser(button.dataset.id);
});
loadUsers();
