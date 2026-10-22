import {
  api,
  changePassword,
  clearSession,
  logout,
  storeUser,
} from "./api.js";
import { escapeHtml, statusLabel } from "./format.js";
import { setButtonLoading, showToast } from "./ui.js";

let currentUser = null;

function homeFor(user) {
  return user?.role === "motorista" ? "/motorista" : "/dashboard";
}

async function initialize() {
  try {
    currentUser = await api("/auth/me", {
      redirectOnUnauthorized: false,
      redirectOnPasswordChange: false,
    });
    storeUser(currentUser);
  } catch {
    clearSession();
    window.location.replace("/login?session=expired");
    return;
  }

  const mandatory = Boolean(currentUser.must_change_password);
  const notice = document.getElementById("mandatoryPasswordNotice");
  const cancel = document.getElementById("cancelPasswordChange");
  notice.hidden = !mandatory;
  cancel.hidden = mandatory;
  cancel.href = homeFor(currentUser);

  const summary = document.getElementById("passwordUser");
  summary.hidden = false;
  summary.innerHTML = `
    <strong>${escapeHtml(currentUser.name)}</strong>
    <span>${escapeHtml(currentUser.email)} • ${escapeHtml(statusLabel(currentUser.role))}</span>
  `;

  document.getElementById("currentPassword").focus();
}

const form = document.getElementById("changePasswordForm");
const submitButton = document.getElementById("changePasswordButton");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const currentPassword = document.getElementById("currentPassword").value;
  const newPassword = document.getElementById("newPassword").value;
  const confirmation = document.getElementById("confirmPassword").value;

  if (newPassword !== confirmation) {
    showToast("A confirmação não corresponde à nova senha.", "error", 5000);
    return;
  }
  if (currentPassword === newPassword) {
    showToast("A nova senha precisa ser diferente da senha atual.", "warning", 5000);
    return;
  }

  setButtonLoading(submitButton, true, "Salvando");
  try {
    await changePassword(currentPassword, newPassword);
    window.location.replace("/login?password=changed");
  } catch (error) {
    showToast(error.message, "error", 6500);
  } finally {
    setButtonLoading(submitButton, false);
  }
});

document.getElementById("passwordLogoutButton").addEventListener("click", async () => {
  try {
    await logout();
  } catch {
    clearSession();
  }
  window.location.replace("/login");
});

initialize();
