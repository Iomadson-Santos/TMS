# TMS - Etapa 1

## Como aplicar no VS Code

1. Faça uma cópia de segurança do projeto atual.
2. Substitua a pasta `backend` pela pasta deste pacote.
3. Abra um terminal na pasta `backend`.
4. Crie o ambiente virtual:

```bash
python -m venv .venv
```

5. Ative-o no Windows:

```powershell
.venv\Scripts\Activate.ps1
```

6. Instale as dependências:

```bash
pip install -r requirements.txt
```

7. Copie `.env.example` para `.env`.
8. Inicie a API:

```bash
uvicorn app.main:app --reload
```

9. Abra `http://127.0.0.1:8000/docs`.

## Compatibilidade

Os caminhos usados pelo frontend foram preservados:

- `/vehicles`
- `/routes`
- `/deliveries`
- `/tracking`

O arquivo `backend/main.py` também foi mantido para deploys que executam `uvicorn main:app`.

## Antes de enviar ao GitHub

```bash
pytest
ruff check app tests
```

## Banco existente

Esta etapa mantém os nomes das tabelas e campos principais. Faça backup do MySQL antes de executar contra o banco de produção. A próxima etapa deve incluir Alembic para controlar migrações.
