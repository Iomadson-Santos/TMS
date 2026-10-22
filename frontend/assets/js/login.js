import { api, login, storeUser } from "./api.js";
import { setButtonLoading, showToast } from "./ui.js";

function homeFor(user) {
  if (user?.must_change_password) return "/change-password";
  return user?.role === "motorista" ? "/motorista" : "/dashboard";
}

const form = document.getElementById("loginForm");
const submitButton = document.getElementById("loginButton");
const lockMessage = document.getElementById("loginLockMessage");
let cooldownTimer = null;
let cooldownUntil = 0;

function stopCooldown() {
  if (cooldownTimer) window.clearInterval(cooldownTimer);
  cooldownTimer = null;
  cooldownUntil = 0;
  lockMessage.hidden = true;
  lockMessage.textContent = "";
  submitButton.disabled = false;
  submitButton.textContent = "Entrar";
}

function updateCooldown() {
  const remaining = Math.max(0, Math.ceil((cooldownUntil - Date.now()) / 1000));
  if (remaining <= 0) {
    stopCooldown();
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = `Tente novamente em ${remaining}s`;
  lockMessage.hidden = false;
  lockMessage.textContent =
    `Acesso temporariamente bloqueado. Aguarde ${remaining} segundo${remaining === 1 ? "" : "s"}.`;
}

function startCooldown(seconds) {
  if (cooldownTimer) window.clearInterval(cooldownTimer);
  cooldownUntil = Date.now() + Math.max(1, seconds) * 1000;
  updateCooldown();
  cooldownTimer = window.setInterval(updateCooldown, 250);
}

async function redirectAuthenticatedUser() {
  try {
    const user = await api("/auth/me", {
      redirectOnUnauthorized: false,
      redirectOnPasswordChange: false,
    });
    storeUser(user);
    window.location.replace(homeFor(user));
  } catch (error) {
    if (error.status !== 401) {
      showToast("Não foi possível validar a sessão atual.", "warning", 4500);
    }
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (cooldownUntil > Date.now()) return;

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  setButtonLoading(submitButton, true, "Entrando");
  try {
    const user = await login(email, password);
    window.location.replace(homeFor(user));
  } catch (error) {
    if (error.status === 429) {
      startCooldown(error.retryAfter || 30);
    }
    showToast(error.message, "error", 6500);
  } finally {
    if (cooldownUntil <= Date.now()) setButtonLoading(submitButton, false);
  }
});

const query = new URLSearchParams(window.location.search);
if (query.get("session") === "expired") {
  showToast("Sua sessão expirou. Entre novamente.", "warning", 5000);
}
if (query.get("password") === "changed") {
  showToast("Senha alterada. Entre novamente com a nova senha.", "success", 6000);
}

redirectAuthenticatedUser();
