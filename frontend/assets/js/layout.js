import { api, clearSession, logout, storeUser } from "./api.js";
import { escapeHtml, statusLabel } from "./format.js";

const NAV_ITEMS = [
  { key: "dashboard", href: "/dashboard", icon: "▦", label: "Dashboard" },
  { key: "deliveries", href: "/deliveries", icon: "▣", label: "Entregas" },
  { key: "routes", href: "/routes", icon: "⌁", label: "Rotas" },
  {
    key: "tracking",
    href: "/tracking",
    icon: "◎",
    label: "Rastreamento",
    roles: ["administrador", "operador"],
  },
  { key: "vehicles", href: "/vehicles", icon: "▰", label: "Veículos" },
  {
    key: "users",
    href: "/users",
    icon: "◉",
    label: "Usuários",
    roles: ["administrador"],
  },
  {
    key: "audit",
    href: "/audit",
    icon: "≡",
    label: "Auditoria",
    roles: ["administrador"],
  },
];

export async function requireAuth(allowedRoles = null) {
  let user;
  try {
    user = await api("/auth/me");
    storeUser(user);
  } catch (error) {
    if (error.status === 401) {
      clearSession();
      if (!window.location.pathname.startsWith("/login")) {
        window.location.replace("/login?session=expired");
      }
    }
    throw error;
  }

  if (user.must_change_password) {
    window.location.replace("/change-password");
    throw new Error("Troca de senha obrigatória");
  }

  const isDriverPage = [
    "/motorista",
    "/motorista.html",
    "/driver",
    "/mobile-driver",
  ].includes(window.location.pathname);

  // O motorista usa uma interface dedicada, com botoes grandes e fluxo de paradas.
  // Ao tentar abrir uma pagina administrativa, ele volta automaticamente ao app mobile.
  if (user.role === "motorista" && !isDriverPage) {
    window.location.replace("/motorista");
    throw new Error("Redirecionando para o aplicativo do motorista");
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    window.location.replace(user.role === "motorista" ? "/motorista" : "/dashboard");
    throw new Error("Acesso negado");
  }
  return user;
}

export async function initLayout(activeKey, allowedRoles = null) {
  const user = await requireAuth(allowedRoles);
  const sidebar = document.getElementById("sidebar");
  const topbar = document.getElementById("topbar");

  if (sidebar) {
    sidebar.className = "sidebar";
    sidebar.innerHTML = `
      <div class="brand">
        <div class="brand-mark">T</div>
        <div class="brand-text">TMS<small>Gestão logística</small></div>
      </div>
      <nav class="nav-list">
        ${NAV_ITEMS.filter(
          (item) => !item.roles || item.roles.includes(user.role)
        )
          .map(
            (item) => `
              <a class="nav-link ${item.key === activeKey ? "active" : ""}" href="${item.href}">
                <span class="nav-icon">${item.icon}</span>
                <span class="nav-label">${item.label}</span>
              </a>
            `
          )
          .join("")}
      </nav>
    `;
  }

  if (topbar) {
    const pageTitle = NAV_ITEMS.find((item) => item.key === activeKey)?.label || "TMS";
    topbar.className = "topbar";
    topbar.innerHTML = `
      <div class="topbar-title">${pageTitle}</div>
      <div class="topbar-user">
        <span id="topbarClock" class="topbar-clock muted small"></span>
        <div class="user-avatar">${escapeHtml(user.name.charAt(0).toUpperCase())}</div>
        <div class="user-text">
          <strong>${escapeHtml(user.name)}</strong>
          <small>${escapeHtml(statusLabel(user.role))}</small>
        </div>
        <a class="btn btn-light btn-sm" href="/change-password?manual=1">Senha</a>
        <button id="logoutButton" class="btn btn-light btn-sm" type="button">Sair</button>
      </div>
    `;

    document.getElementById("logoutButton")?.addEventListener("click", async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      button.textContent = "Saindo...";
      try {
        await logout();
      } catch {
        clearSession();
      }
      window.location.replace("/login");
    });

    const updateClock = () => {
      const clock = document.getElementById("topbarClock");
      if (clock) {
        clock.textContent = new Intl.DateTimeFormat("pt-BR", {
          dateStyle: "short",
          timeStyle: "medium",
        }).format(new Date());
      }
    };
    updateClock();
    window.setInterval(updateClock, 1000);
  }

  return user;
}
