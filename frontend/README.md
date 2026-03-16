# TMS – Sistema de Gestão de Frota Própria

Stack: **FastAPI + MySQL + HTML/CSS puro**  
Módulos: **Roteirização & Otimização** · **Rastreamento em Tempo Real**

---

## Estrutura do Projeto

```
tms/
├── backend/
│   ├── main.py               # Entry point FastAPI
│   ├── requirements.txt
│   ├── .env.example          # Copie para .env e configure
│   ├── core/
│   │   └── database.py       # Conexão MySQL + SQLAlchemy
│   ├── models/
│   │   └── models.py         # Tabelas: Vehicle, Route, Stop, Tracking
│   ├── schemas/
│   │   └── schemas.py        # Validação Pydantic
│   └── routers/
│       ├── vehicles.py       # CRUD de veículos
│       ├── routes.py         # CRUD de rotas + otimização (nearest neighbor)
│       └── tracking.py       # Rastreamento + WebSocket
└── frontend/
    ├── index.html            # Dashboard principal com mapa
    ├── vehicles.html         # Gestão da frota
    ├── routes.html           # Criação e otimização de rotas
    └── tracking.html         # Rastreamento ao vivo
```

---

## Setup – Backend

### 1. Criar banco MySQL

```sql
CREATE DATABASE tms_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. Configurar variáveis de ambiente

```bash
cd backend
cp .env.example .env
# Edite .env com suas credenciais MySQL
```

### 3. Instalar dependências e rodar

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

As tabelas são criadas automaticamente no primeiro start.

### 4. Acessar documentação interativa (Swagger)

```
http://localhost:8000/docs
```

---

## Setup – Frontend

Abra os arquivos diretamente no navegador (não precisa de servidor):

```bash
open frontend/index.html
# ou simplesmente arraste o arquivo no Chrome/Firefox
```

> O frontend funciona em **modo demo** mesmo sem o backend rodando,  
> usando dados simulados para visualização.

---

## Endpoints Principais

### Veículos
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/vehicles/` | Listar todos |
| POST | `/vehicles/` | Cadastrar |
| PATCH | `/vehicles/{id}` | Atualizar |
| DELETE | `/vehicles/{id}` | Remover |

### Rotas
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/routes/` | Listar rotas |
| POST | `/routes/` | Criar rota com paradas |
| POST | `/routes/otimizar` | **Otimizar rota (nearest neighbor)** |
| PATCH | `/routes/{id}` | Atualizar status |
| PATCH | `/routes/{id}/stops/{stop_id}/concluir` | Marcar parada concluída |

### Rastreamento
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/tracking/all/latest` | Última posição de todos os veículos |
| GET | `/tracking/{vehicle_id}` | Histórico de um veículo |
| POST | `/tracking/` | Registrar nova posição (dispara broadcast WS) |
| WS | `/tracking/ws/all/live` | **WebSocket – todos os veículos ao vivo** |
| WS | `/tracking/ws/{vehicle_id}` | WebSocket – veículo específico |

---

## Algoritmo de Otimização

O endpoint `POST /routes/otimizar` implementa o algoritmo **Nearest Neighbor (Vizinho Mais Próximo)**:

1. Parte da origem
2. A cada passo, vai para a parada não visitada mais próxima (distância Haversine)
3. Repete até visitar todas as paradas
4. Retorna a rota otimizada, distância total e economia estimada em km

Complexidade: O(n²) – adequado para frotas com até ~200 paradas por rota.

---

## Próximos Módulos Sugeridos

- [ ] **Autenticação** – JWT com roles (admin, motorista, operador)
- [ ] **Módulo Financeiro** – Custo por rota, combustível, pedágios
- [ ] **App Motorista** – PWA com atualização de posição automática
- [ ] **Notificações** – Alertas de atraso, desvio de rota, parada prolongada
- [ ] **Relatórios** – PDF com histórico de rotas e KPIs da frota
- [ ] **Otimização avançada** – OR-Tools (Google) para VRP completo
