export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function formatDate(value, withTime = false) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    ...(withTime ? { timeStyle: "short" } : {}),
  }).format(date);
}

export function formatCurrency(value) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number(value || 0));
}

export function formatNumber(value, decimals = 0) {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(Number(value || 0));
}

export function statusLabel(status) {
  const labels = {
    administrador: "Administrador",
    operador: "Operador",
    motorista: "Motorista",
    disponivel: "Disponivel",
    em_rota: "Em rota",
    manutencao: "Manutencao",
    inativo: "Inativo",
    recebida: "Recebida",
    separada: "Separada",
    faturada: "Faturada",
    pendente: "Pendente",
    entregue: "Entregue",
    devolvida: "Devolvida",
    cancelada: "Cancelada",
    aberta: "Aberta",
    em_andamento: "Em andamento",
    concluida: "Concluida",
    create: "Criacao",
    update: "Alteracao",
    delete: "Exclusao",
    login: "Login realizado",
    login_failed: "Falha de login",
    login_locked: "Login bloqueado",
    logout: "Saída do sistema",
    logout_all: "Encerramento de todas as sessões",
    session_revoke: "Sessão revogada",
    refresh_failed: "Falha ao renovar sessão",
    refresh_reuse: "Reutilização de credencial detectada",
    refresh_stale: "Renovação concorrente de sessão",
    password_change: "Troca de senha",
    password_change_failed: "Senha atual incorreta",
    password_change_locked: "Troca de senha bloqueada",
    status_change: "Mudança de status",
    optimize: "Otimizacao",
    assign_route: "Vinculo de rota",
    remove_route: "Remocao de rota",
  };
  return labels[status] || String(status || "—").replaceAll("_", " ");
}

export function badgeClass(status) {
  const success = ["disponivel", "entregue", "concluida", "administrador"];
  const warning = ["em_rota", "em_andamento", "manutencao", "pendente", "faturada"];
  const danger = ["inativo", "cancelada", "devolvida"];
  const info = ["aberta", "recebida", "separada", "operador", "motorista"];
  if (success.includes(status)) return "success";
  if (warning.includes(status)) return "warning";
  if (danger.includes(status)) return "danger";
  if (info.includes(status)) return "info";
  return "";
}
