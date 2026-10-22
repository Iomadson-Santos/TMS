# TMS Ciranda — 1.0.0-rc1 preparado para homologacao e producao


> **Release candidate:** esta pasta inclui os arquivos de infraestrutura para Render, PostgreSQL gerenciado, CI no GitHub Actions, health check de banco, criacao segura do primeiro administrador e teste online. Publique primeiro com `render.staging.yaml`; use `render.yaml` apenas depois de aprovar a homologacao.

Documentos principais desta etapa:

- [`DEPLOY_RENDER_PASSO_A_PASSO.md`](DEPLOY_RENDER_PASSO_A_PASSO.md)
- [`CHECKLIST_HOMOLOGACAO_PRODUCAO.md`](CHECKLIST_HOMOLOGACAO_PRODUCAO.md)
- [`VALIDATION_PRODUCTION_RC1.md`](VALIDATION_PRODUCTION_RC1.md)

Base executável de um TMS em FastAPI, SQLAlchemy 2, Pydantic 2 e frontend HTML/CSS/JavaScript. O FastAPI serve a API e as páginas; não é necessário iniciar outro servidor para o frontend.

A versão 0.1.4.1 inclui a correção do mapa de rastreamento e mantém os módulos de usuários, veículos, entregas, rotas, aplicativo mobile do motorista, rastreamento e auditoria. O foco da 0.1.4 é reduzir os riscos mais comuns antes de uma futura publicação na internet.

> Segurança não é um estado definitivo. Esta versão inclui endurecimento de código e testes automatizados, mas a publicação ainda depende de configuração correta, HTTPS, PostgreSQL, atualizações do servidor, backups testados e revisão externa do ambiente.

## Controles de segurança incluídos

- Terceira senha incorreta bloqueia temporariamente o identificador por 30 segundos.
- Novas sequências de três falhas dentro da janela de 15 minutos aumentam o bloqueio para 60, 120, 240 e no máximo 300 segundos.
- Limite adicional por IP: 20 falhas por padrão.
- O mesmo limite de três erros protege a confirmação da senha atual ao trocá-la.
- Resposta de login genérica, evitando revelar se o e-mail existe, está inativo ou teve a senha errada.
- Argon2id para hash de senhas e política de senha previsível/fraca.
- Troca de senha obrigatória para contas antigas e novas contas criadas pelo administrador.
- Access token de curta duração em cookie `HttpOnly`; o JWT não fica no `localStorage`.
- Refresh token opaco, armazenado somente como HMAC, com rotação e detecção de reutilização.
- Revogação de sessão no logout, troca de senha, alteração de e-mail, perfil ou situação do usuário.
- Proteção CSRF assinada para operações autenticadas por cookie.
- Validação de origem, CORS restritivo em produção e hosts permitidos.
- Cabeçalhos de segurança, incluindo CSP, anti-frame, `nosniff`, política de referência e HSTS quando HTTPS estiver ativo.
- Limite global de 1 MiB por corpo de requisição, configurável.
- Validação Pydantic com campos desconhecidos rejeitados e erros que não repetem senhas recebidas.
- Permissões por perfil e verificação de propriedade das rotas/entregas do motorista no backend.
- Auditoria de login, falhas, bloqueios, sessões, troca de senha e operações de negócio.
- Preflight que impede a inicialização em produção com configurações perigosas.
- Rotação de logs e rotinas de backup para SQLite/PostgreSQL.

A descrição completa está em [`SEGURANCA.md`](SEGURANCA.md). O roteiro de publicação está em [`DEPLOY_PRODUCTION.md`](DEPLOY_PRODUCTION.md).

## Atualizar a instalação 0.1.3 no Windows

1. Pare o servidor com `Ctrl + C`.
2. Copie a pasta atual ou, no mínimo, `backend\.env` e `backend\tms.db` para um local de backup.
3. Extraia o ZIP de atualização na pasta que contém `tms_ciranda_starter` e confirme a substituição.
4. Na raiz já atualizada, execute `backup_windows.bat` para criar também um backup consistente do banco.
5. Aplique as migrações e configurações:

```bat
update_windows.bat
```

6. Inicie normalmente:

```bat
run_windows.bat
```

7. Abra `http://127.0.0.1:8000` e pressione `Ctrl + F5` uma vez.

O atualizador preserva `.venv`, `backend/.env` e `backend/tms.db`. Ele cria uma cópia do `.env` antigo, gera uma `SECRET_KEY` local aleatória quando encontra a chave padrão, reduz o access token legado de 480 para 15 minutos e aplica as migrações. Consulte [`ATUALIZACAO_0.1.4.md`](ATUALIZACAO_0.1.4.md).

## Primeira instalação local no Windows

1. Extraia o projeto.
2. Abra a pasta no VS Code.
3. Execute `setup_windows.bat`.
4. Execute `run_windows.bat`.
5. Acesse `http://127.0.0.1:8000`.

O ambiente local contém contas e dados de demonstração. Todas as contas devem trocar a senha no primeiro acesso à versão 0.1.4.

### Logins de demonstração local

```text
Administrador
admin@tmsciranda.com.br
Admin123!

Operador
operador@tmsciranda.com.br
Operador123!

Motorista
motorista@tmsciranda.com.br
Motorista123!
```

Essas credenciais são públicas e **nunca podem existir em produção**. O preflight bloqueia a publicação enquanto alguma dessas contas ainda existir com a senha conhecida.

## Endereços locais

- Administrativo: `http://127.0.0.1:8000`
- Motorista: `http://127.0.0.1:8000/motorista`
- Rastreamento: `http://127.0.0.1:8000/tracking`
- Swagger local: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/v1/health`

## Ferramentas de revisão automatizada

Em um computador com internet, instale as ferramentas extras uma vez:

```bat
setup_security_tools_windows.bat
```

Depois execute:

```bat
security_review_windows.bat
```

O script roda compilação, testes, Ruff, Bandit, auditoria de dependências e, quando Node.js está instalado, verificação de sintaxe dos JavaScripts. Resultados anteriores não substituem uma nova execução imediatamente antes da publicação.

## Produção

Não exponha `run_windows.bat` diretamente na internet. A publicação preparada por esta versão exige:

- PostgreSQL;
- domínio próprio e HTTPS em proxy reverso;
- `.env` criado a partir de `.env.production.example`;
- `SECRET_KEY` aleatória;
- contas de demonstração removidas;
- backups e restauração testados;
- firewall e atualizações do sistema operacional;
- execução do preflight e dos scanners no ambiente final.

Leia [`DEPLOY_PRODUCTION.md`](DEPLOY_PRODUCTION.md) antes de publicar.

## Documentação desta versão

- [`ATUALIZACAO_0.1.4.md`](ATUALIZACAO_0.1.4.md): instalação sobre a versão atual.
- [`SEGURANCA.md`](SEGURANCA.md): controles implementados e parâmetros.
- [`DEPLOY_PRODUCTION.md`](DEPLOY_PRODUCTION.md): checklist de publicação.
- [`VALIDATION_0.1.4.md`](VALIDATION_0.1.4.md): testes executados e limitações.
- [`RASTREAMENTO.md`](RASTREAMENTO.md): funcionamento e privacidade do GPS.
