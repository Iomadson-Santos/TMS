// ── Shared TMS UI ────────────────────────────────────────
const TMS = {
  API: 'https://tms-production-3fba.up.railway.app',

  // Inject sidebar + topbar into page
  initLayout(activePage) {
    // Font
    const font = document.createElement('link');
    font.rel = 'stylesheet';
    font.href = 'https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&family=Manrope:wght@300;400;500;600&display=swap';
    document.head.appendChild(font);

    // Global styles
    const style = document.createElement('style');
    style.textContent = `
      :root {
        --bg: #0a0c10;
        --surface: #111318;
        --surface2: #181c23;
        --surface3: #1e232d;
        --border: #2a3040;
        --border2: #364055;
        --accent: #3b82f6;
        --accent-glow: rgba(59,130,246,.25);
        --green: #22c55e;
        --green-glow: rgba(34,197,94,.2);
        --yellow: #eab308;
        --red: #ef4444;
        --orange: #f97316;
        --text: #e2e8f0;
        --text2: #94a3b8;
        --text3: #4b5a6e;
        --mono: 'IBM Plex Mono', monospace;
        --display: 'Syne', sans-serif;
        --body: 'Manrope', sans-serif;
        --sidebar-w: 230px;
      }
      *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
      html, body { height: 100%; }
      body {
        background: var(--bg);
        color: var(--text);
        font-family: var(--body);
        display: flex;
        font-size: 14px;
        line-height: 1.5;
      }
      a { text-decoration: none; color: inherit; }
      button { cursor: pointer; font-family: var(--body); }
      input, select, textarea { font-family: var(--body); }
      ::-webkit-scrollbar { width: 4px; height: 4px; }
      ::-webkit-scrollbar-track { background: transparent; }
      ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

      /* ── Sidebar ── */
      .sidebar {
        width: var(--sidebar-w);
        background: var(--surface);
        border-right: 1px solid var(--border);
        display: flex;
        flex-direction: column;
        position: fixed;
        top: 0; left: 0; bottom: 0;
        z-index: 200;
        flex-shrink: 0;
      }
      .sidebar-logo {
        padding: 20px 20px 16px;
        border-bottom: 1px solid var(--border);
      }
      .logo-mark {
        font-family: var(--display);
        font-size: 20px;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: var(--text);
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .logo-mark .dot {
        width: 8px; height: 8px;
        border-radius: 2px;
        background: var(--accent);
        box-shadow: 0 0 10px var(--accent);
      }
      .logo-sub {
        font-size: 10px;
        font-family: var(--mono);
        color: var(--text3);
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-top: 2px;
      }

      .sidebar-section {
        padding: 16px 12px 8px;
      }
      .sidebar-section-label {
        font-size: 9px;
        font-family: var(--mono);
        color: var(--text3);
        text-transform: uppercase;
        letter-spacing: 2px;
        padding: 0 8px;
        margin-bottom: 6px;
      }
      .nav-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 9px 10px;
        border-radius: 8px;
        color: var(--text2);
        font-size: 13px;
        font-weight: 500;
        transition: all .15s;
        margin-bottom: 2px;
        position: relative;
      }
      .nav-item:hover { background: var(--surface2); color: var(--text); }
      .nav-item.active {
        background: rgba(59,130,246,.12);
        color: var(--accent);
        font-weight: 600;
      }
      .nav-item.active::before {
        content: '';
        position: absolute;
        left: 0; top: 6px; bottom: 6px;
        width: 3px;
        background: var(--accent);
        border-radius: 0 2px 2px 0;
        box-shadow: 0 0 8px var(--accent);
      }
      .nav-icon { font-size: 16px; width: 20px; text-align: center; }
      .nav-badge {
        margin-left: auto;
        background: var(--accent);
        color: #fff;
        font-size: 9px;
        font-family: var(--mono);
        font-weight: 600;
        padding: 1px 6px;
        border-radius: 10px;
      }

      .sidebar-footer {
        margin-top: auto;
        padding: 12px;
        border-top: 1px solid var(--border);
      }
      .sidebar-status {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 10px;
        background: var(--surface2);
        border-radius: 8px;
        font-size: 11px;
        color: var(--text2);
        font-family: var(--mono);
      }
      .status-dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        background: var(--green);
        box-shadow: 0 0 6px var(--green);
        animation: blink 2s infinite;
        flex-shrink: 0;
      }
      .status-dot.offline { background: var(--red); box-shadow: 0 0 6px var(--red); animation: none; }
      @keyframes blink { 0%,100%{opacity:1} 50%{opacity:.4} }

      /* ── Main content ── */
      .main-wrap {
        margin-left: var(--sidebar-w);
        flex: 1;
        display: flex;
        flex-direction: column;
        min-height: 100vh;
        min-width: 0;
      }
      .topbar {
        height: 54px;
        background: var(--surface);
        border-bottom: 1px solid var(--border);
        display: flex;
        align-items: center;
        padding: 0 24px;
        gap: 16px;
        position: sticky;
        top: 0;
        z-index: 100;
      }
      .topbar-title {
        font-family: var(--display);
        font-size: 16px;
        font-weight: 700;
      }
      .topbar-breadcrumb {
        font-size: 11px;
        font-family: var(--mono);
        color: var(--text3);
        margin-left: 4px;
      }
      .topbar-right {
        margin-left: auto;
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .topbar-time {
        font-family: var(--mono);
        font-size: 12px;
        color: var(--text3);
      }

      /* ── Buttons ── */
      .btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        padding: 7px 14px;
        transition: all .15s;
        border: none;
      }
      .btn-primary { background: var(--accent); color: #fff; }
      .btn-primary:hover { background: #2563eb; box-shadow: 0 0 16px var(--accent-glow); }
      .btn-secondary { background: var(--surface2); color: var(--text2); border: 1px solid var(--border); }
      .btn-secondary:hover { color: var(--text); border-color: var(--border2); }
      .btn-danger { background: rgba(239,68,68,.1); color: var(--red); border: 1px solid rgba(239,68,68,.2); }
      .btn-danger:hover { background: rgba(239,68,68,.2); }

      /* ── Badges ── */
      .badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 10px;
        font-family: var(--mono);
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        letter-spacing: .3px;
      }
      .badge::before { content:''; width:5px; height:5px; border-radius:50%; }
      .badge-green { background: rgba(34,197,94,.1); color: var(--green); border: 1px solid rgba(34,197,94,.2); }
      .badge-green::before { background: var(--green); }
      .badge-blue { background: rgba(59,130,246,.1); color: var(--accent); border: 1px solid rgba(59,130,246,.2); }
      .badge-blue::before { background: var(--accent); }
      .badge-yellow { background: rgba(234,179,8,.1); color: var(--yellow); border: 1px solid rgba(234,179,8,.2); }
      .badge-yellow::before { background: var(--yellow); }
      .badge-red { background: rgba(239,68,68,.1); color: var(--red); border: 1px solid rgba(239,68,68,.2); }
      .badge-red::before { background: var(--red); }
      .badge-gray { background: var(--surface3); color: var(--text3); border: 1px solid var(--border); }
      .badge-gray::before { background: var(--text3); }

      /* ── Cards ── */
      .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 20px;
      }
      .card-title {
        font-size: 11px;
        font-family: var(--mono);
        color: var(--text3);
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 10px;
      }

      /* ── KPI ── */
      .kpi-value {
        font-family: var(--display);
        font-size: 32px;
        font-weight: 800;
        line-height: 1;
        margin-bottom: 4px;
      }
      .kpi-sub { font-size: 12px; color: var(--text2); }
      .kpi-delta {
        font-size: 11px;
        font-family: var(--mono);
        margin-top: 8px;
      }
      .kpi-delta.up { color: var(--green); }
      .kpi-delta.down { color: var(--red); }

      /* ── Table ── */
      .table-wrap { overflow-x: auto; }
      table { width: 100%; border-collapse: collapse; font-size: 13px; }
      thead th {
        text-align: left;
        padding: 10px 14px;
        font-size: 10px;
        font-family: var(--mono);
        color: var(--text3);
        text-transform: uppercase;
        letter-spacing: 1px;
        border-bottom: 1px solid var(--border);
        white-space: nowrap;
      }
      tbody tr {
        border-bottom: 1px solid var(--border);
        transition: background .1s;
      }
      tbody tr:last-child { border-bottom: none; }
      tbody tr:hover { background: var(--surface2); }
      tbody td { padding: 11px 14px; color: var(--text2); vertical-align: middle; }
      tbody td:first-child { color: var(--text); font-weight: 500; }

      /* ── Search/Filter bar ── */
      .toolbar {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 16px;
        flex-wrap: wrap;
      }
      .search-wrap {
        position: relative;
        flex: 1;
        min-width: 200px;
      }
      .search-icon {
        position: absolute;
        left: 11px;
        top: 50%;
        transform: translateY(-50%);
        color: var(--text3);
        font-size: 13px;
        pointer-events: none;
      }
      .search-input {
        width: 100%;
        background: var(--surface2);
        border: 1px solid var(--border);
        border-radius: 8px;
        color: var(--text);
        font-size: 13px;
        padding: 8px 12px 8px 34px;
        outline: none;
        transition: border-color .15s;
      }
      .search-input:focus { border-color: var(--accent); }
      .search-input::placeholder { color: var(--text3); }
      .filter-select {
        background: var(--surface2);
        border: 1px solid var(--border);
        border-radius: 8px;
        color: var(--text2);
        font-size: 12px;
        padding: 8px 12px;
        outline: none;
        cursor: pointer;
      }
      .filter-select:focus { border-color: var(--accent); }

      /* ── Forms ── */
      .form-group { margin-bottom: 14px; }
      .form-label {
        display: block;
        font-size: 10px;
        font-family: var(--mono);
        color: var(--text3);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 5px;
      }
      .form-input, .form-select {
        width: 100%;
        background: var(--surface2);
        border: 1px solid var(--border);
        border-radius: 8px;
        color: var(--text);
        font-size: 13px;
        padding: 9px 12px;
        outline: none;
        transition: border-color .15s;
      }
      .form-input:focus, .form-select:focus { border-color: var(--accent); }
      .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

      /* ── Modal ── */
      .modal-backdrop {
        position: fixed; inset: 0;
        background: rgba(0,0,0,.75);
        backdrop-filter: blur(6px);
        z-index: 900;
        display: none;
        align-items: center;
        justify-content: center;
      }
      .modal-backdrop.show { display: flex; }
      .modal {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 16px;
        width: 500px;
        max-height: 88vh;
        overflow-y: auto;
        padding: 28px;
        animation: modalIn .2s ease;
      }
      @keyframes modalIn { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
      .modal-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 22px;
      }
      .modal-title { font-family: var(--display); font-size: 17px; font-weight: 700; }
      .modal-close {
        background: var(--surface2);
        border: 1px solid var(--border);
        color: var(--text2);
        border-radius: 6px;
        width: 28px; height: 28px;
        display: flex; align-items: center; justify-content: center;
        font-size: 14px;
      }
      .modal-close:hover { color: var(--text); border-color: var(--border2); }
      .modal-footer { display: flex; gap: 10px; margin-top: 22px; }

      /* ── Page layout ── */
      .page { padding: 24px; flex: 1; }
      .page-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        margin-bottom: 24px;
      }
      .page-title { font-family: var(--display); font-size: 22px; font-weight: 800; }
      .page-sub { font-size: 12px; color: var(--text2); margin-top: 3px; }

      .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
      .grid-3 { display: grid; grid-template-columns: repeat(3,1fr); gap: 16px; }
      .grid-4 { display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; }

      .empty-state {
        text-align: center;
        padding: 48px 24px;
        color: var(--text3);
      }
      .empty-icon { font-size: 40px; margin-bottom: 12px; }
      .empty-text { font-size: 13px; }
    `;
    document.head.appendChild(style);

    // Build sidebar HTML
    const pages = [
      { id: 'index', icon: '⬡', label: 'Dashboard', href: 'index.html' },
      { id: 'vehicles', icon: '🚛', label: 'Veículos', href: 'vehicles.html' },
      { id: 'routes', icon: '🗺', label: 'Rotas', href: 'routes.html' },
      { id: 'deliveries', icon: '📦', label: 'Entregas', href: 'deliveries.html' },
      { id: 'tracking', icon: '📡', label: 'Rastreamento ao Vivo', href: 'tracking.html' },
      { id: 'audit', icon: '📋', label: 'Auditoria', href: 'audit.html' },
    ];

    const sidebar = document.createElement('aside');
    sidebar.className = 'sidebar';
    sidebar.innerHTML = `
      <div class="sidebar-logo">
        <div class="logo-mark"><div class="dot"></div>TMS</div>
        <div class="logo-sub">Gestão de Frota</div>
      </div>
      <div class="sidebar-section">
        <div class="sidebar-section-label">Menu</div>
        ${pages.map(p => `
          <a href="${p.href}" class="nav-item ${activePage === p.id ? 'active' : ''}">
            <span class="nav-icon">${p.icon}</span>
            <span>${p.label}</span>
          </a>
        `).join('')}
      </div>
      <div class="sidebar-footer">
        <div class="sidebar-status">
          <div class="status-dot" id="apiDot"></div>
          <span id="apiLabel">Verificando API...</span>
        </div>
      </div>
    `;
    document.body.prepend(sidebar);

    // Wrap existing content
    const content = Array.from(document.body.children).filter(el => el !== sidebar);
    const wrap = document.createElement('div');
    wrap.className = 'main-wrap';
    content.forEach(el => wrap.appendChild(el));
    document.body.appendChild(wrap);
    // Footer
    const footer = document.createElement('div');
    footer.style.cssText = 'padding:8px 24px;font-size:10px;font-family:var(--mono);color:var(--text3);border-top:1px solid var(--border);background:var(--surface);text-align:right;flex-shrink:0;';
    footer.innerHTML = '© 2026 <strong style="color:var(--text2)">Iomadson Santos</strong> · TMS Sistema de Gestão de Frota';
    wrap.appendChild(footer);

    // Clock
    const timeEl = document.querySelector('.topbar-time');
    if (timeEl) {
      setInterval(() => timeEl.textContent = new Date().toLocaleTimeString('pt-BR'), 1000);
    }

    // API health check
    fetch(TMS.API + '/health')
      .then(() => {
        document.getElementById('apiDot').className = 'status-dot';
        document.getElementById('apiLabel').textContent = 'API Online';
      })
      .catch(() => {
        document.getElementById('apiDot').className = 'status-dot offline';
        document.getElementById('apiLabel').textContent = 'API Offline';
      });
  },

  statusMap: {
    disponivel: ['badge-green', 'Disponível'],
    em_rota:    ['badge-blue',  'Em Rota'],
    manutencao: ['badge-yellow','Manutenção'],
    inativo:    ['badge-gray',  'Inativo'],
    planejada:  ['badge-gray',  'Planejada'],
    em_andamento: ['badge-blue','Em Andamento'],
    concluida:  ['badge-green', 'Concluída'],
    cancelada:  ['badge-red',   'Cancelada'],
  },

  badge(status) {
    const [cls, label] = this.statusMap[status] || ['badge-gray', status];
    return `<span class="badge ${cls}">${label}</span>`;
  },

  async fetchVehicles() {
    try {
      const r = await fetch(TMS.API + '/vehicles/');
      return await r.json();
    } catch {
      return [
        {id:1,placa:'BRA-2E19',modelo:'VW Delivery 9.170',tipo:'caminhao',status:'em_rota',motorista:'Carlos Silva',telefone_motorista:'(11)98765-4321',capacidade_kg:9000,lat_atual:-23.543,lng_atual:-46.628},
        {id:2,placa:'ABC-1D23',modelo:'Fiat Ducato',tipo:'van',status:'disponivel',motorista:'Ana Lima',telefone_motorista:'(11)91234-5678',capacidade_kg:1500,lat_atual:-23.561,lng_atual:-46.654},
        {id:3,placa:'XYZ-3A01',modelo:'Honda CG 160',tipo:'moto',status:'disponivel',motorista:'Pedro Souza',telefone_motorista:null,capacidade_kg:50,lat_atual:-23.530,lng_atual:-46.640},
        {id:4,placa:'DEF-4B56',modelo:'Mercedes Atego',tipo:'caminhao',status:'manutencao',motorista:'João Costa',telefone_motorista:'(11)93344-5566',capacidade_kg:7000,lat_atual:-23.550,lng_atual:-46.620},
      ];
    }
  },

  async fetchRoutes() {
    try {
      const r = await fetch(TMS.API + '/routes/');
      return await r.json();
    } catch {
      return [
        {id:1,nome:'Rota Centro SP',status:'em_andamento',distancia_km:42.5,tempo_estimado_min:90,carga_total_kg:3200,vehicle_id:1,criado_em:'2026-03-15T08:00:00',paradas:[
          {id:1,ordem:1,endereco:'Av. Paulista, 1000',lat:-23.561,lng:-46.655,concluida:true,destinatario:'Cliente A',carga_kg:800},
          {id:2,ordem:2,endereco:'R. Augusta, 500',lat:-23.553,lng:-46.648,concluida:false,destinatario:'Cliente B',carga_kg:1200},
          {id:3,ordem:3,endereco:'Al. Santos, 200',lat:-23.558,lng:-46.660,concluida:false,destinatario:'Cliente C',carga_kg:1200},
        ]},
        {id:2,nome:'Rota Zona Sul',status:'planejada',distancia_km:28.0,tempo_estimado_min:65,carga_total_kg:1800,vehicle_id:2,criado_em:'2026-03-15T09:00:00',paradas:[
          {id:4,ordem:1,endereco:'R. Domingos de Morais, 300',lat:-23.590,lng:-46.640,concluida:false,destinatario:'Cliente D',carga_kg:900},
          {id:5,ordem:2,endereco:'Av. Jabaquara, 1500',lat:-23.610,lng:-46.645,concluida:false,destinatario:'Cliente E',carga_kg:900},
        ]},
        {id:3,nome:'Rota ABC Paulista',status:'concluida',distancia_km:55.2,tempo_estimado_min:120,carga_total_kg:4500,vehicle_id:1,criado_em:'2026-03-14T07:00:00',paradas:[]},
        {id:4,nome:'Rota Guarulhos',status:'cancelada',distancia_km:38.0,tempo_estimado_min:80,carga_total_kg:2000,vehicle_id:3,criado_em:'2026-03-14T10:00:00',paradas:[]},
      ];
    }
  }
};
