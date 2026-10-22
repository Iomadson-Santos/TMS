# Publicação segura — checklist de produção

Não use `run_windows.bat` para expor o TMS diretamente à internet. Esse arquivo é destinado ao desenvolvimento local e executa Uvicorn com recarga automática.

## Arquitetura mínima recomendada

```text
Internet
  ↓ HTTPS 443
Proxy reverso (Caddy/Nginx/IIS)
  ↓ somente localhost
Uvicorn 127.0.0.1:8000
  ↓ rede privada
PostgreSQL
```

O proxy deve ser o único processo exposto. A porta 8000 não deve estar aberta no firewall externo.

## 1. Servidor e banco

- Use um servidor suportado e atualizado.
- Crie PostgreSQL separado do banco de desenvolvimento.
- Crie um usuário de banco exclusivo do TMS, sem permissões de superusuário.
- Restrinja o PostgreSQL à rede/host necessário.
- Configure backup gerenciado ou `pg_dump` e teste uma restauração completa.

SQLite é bloqueado em `ENVIRONMENT=production`.

## 2. Variáveis de ambiente

Na pasta `backend`, copie:

```text
.env.production.example → .env
```

Substitua todos os valores `SEU_`/`SUBSTITUA_`. Gere a chave com:

```bat
cd backend
..\.venv\Scripts\python.exe -m app.scripts.generate_secret
```

Exemplo de pontos obrigatórios:

```env
ENVIRONMENT=production
PUBLIC_BASE_URL=https://tms.seudominio.com.br
SECRET_KEY=VALOR_ALEATORIO_LONGO
DATABASE_URL=postgresql+psycopg://usuario:senha@127.0.0.1:5432/tms
AUTO_CREATE_TABLES=false
BOOTSTRAP_ADMIN_ENABLED=false
DEMO_SEED_ENABLED=false
ENABLE_API_DOCS=false
ENABLE_API_TOKEN_ENDPOINT=false
AUTH_COOKIE_NAME=__Host-tms_session
REFRESH_COOKIE_NAME=__Host-tms_refresh
CSRF_COOKIE_NAME=__Host-tms_csrf
COOKIE_SECURE=true
COOKIE_DOMAIN=
CORS_ORIGINS=https://tms.seudominio.com.br
ALLOWED_HOSTS=tms.seudominio.com.br
FORCE_HTTPS=true
HSTS_ENABLED=true
PASSWORD_MIN_LENGTH=15
LOG_FILE=../logs/tms.log
```

Não envie `.env`, banco, backups, certificados ou logs para Git/GitHub.

## 3. Migrações e primeiro administrador

Com o banco criado e o `.env` de produção pronto:

```bat
cd backend
..\.venv\Scripts\python.exe -m app.scripts.security_check --config-only
..\.venv\Scripts\python.exe -m app.scripts.update_database
```

Crie o primeiro administrador localmente, sem passar senha na linha de comando:

```bat
cd ..
create_admin_windows.bat
```

A senha é lida sem ser exibida e a conta precisa alterá-la no primeiro login. Não execute `app.scripts.seed` em produção; o próprio script impede isso.

## 4. Revisão automatizada antes do deploy

Em uma máquina conectada à internet:

```bat
setup_security_tools_windows.bat
security_review_windows.bat
```

Esse processo deve ser repetido na versão exata que será publicada. Um resultado antigo não garante que uma dependência continue sem vulnerabilidades conhecidas.

Depois execute o preflight completo:

```bat
cd backend
..\.venv\Scripts\python.exe -m app.scripts.security_check
```

Corrija todos os itens `[ERRO]`. Avalie também cada `[AVISO]`.

## 5. Proxy HTTPS

Configure certificado válido e redirecionamento HTTP → HTTPS no proxy. Encaminhe para `127.0.0.1:8000`. Preserve o host e envie os cabeçalhos de proxy apenas a partir do próprio proxy.

Defina no sistema operacional, quando necessário:

```text
TMS_FORWARDED_ALLOW_IPS=127.0.0.1
```

Não use `*` para aceitar cabeçalhos encaminhados de qualquer IP.

Habilite HSTS somente depois de confirmar que todo o domínio e, caso `includeSubDomains=true`, todos os subdomínios funcionam permanentemente por HTTPS.

## 6. Inicialização

Depois de aprovar configuração, migrações e banco:

```bat
run_production_windows.bat
```

Esse script:

- executa o preflight;
- aplica migrações;
- valida novamente o banco;
- inicia Uvicorn em `127.0.0.1:8000`;
- remove o cabeçalho de servidor;
- aceita headers de proxy somente dos IPs configurados.

Em um servidor real, transforme o processo em serviço com reinicialização automática e conta de sistema sem privilégios administrativos.

## 7. Depois de publicar

- Entre com o administrador e conclua a troca obrigatória de senha.
- Crie usuários individuais; não compartilhe contas.
- Remova ou desative qualquer conta de teste.
- Verifique auditoria de logins e bloqueios.
- Teste `403` do motorista contra rotas de outro usuário.
- Teste backup e restauração em ambiente separado.
- Configure alertas para muitos `login_locked`, `refresh_reuse`, erros 500 e indisponibilidade.
- Faça varredura externa de TLS, cabeçalhos e portas.
- Faça teste de invasão independente antes de armazenar dados reais sensíveis ou rastreamento em escala.

## 8. Backup

Manual:

```bat
backup_windows.bat
```

Em PostgreSQL, o script exige `pg_dump`. Agende-o fora do diretório público e mantenha cópia criptografada em outro local. O backup só é confiável depois de uma restauração testada.

## 9. Rollback

Antes de cada atualização:

1. pare ou coloque a aplicação em manutenção;
2. faça backup do banco;
3. guarde o ZIP da versão anterior;
4. aplique a migração;
5. execute testes de login, permissões, rotas e auditoria;
6. em falha, restaure código e banco como um conjunto compatível.

Não faça downgrade de migração em um banco real sem avaliar perda de dados.
