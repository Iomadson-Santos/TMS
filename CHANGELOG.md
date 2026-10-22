# Changelog

## 1.0.0-rc1.1 — correcao do CI Ruff

- Adicionadas importacoes protegidas por `TYPE_CHECKING` nos modelos SQLAlchemy.
- Corrigidas as 18 referencias de tipos que o Ruff classificava como `F821`.
- Nenhuma alteracao de banco, endpoint, regra operacional ou dependencia.

## 1.0.0-rc1 — preparacao para homologacao e producao

- Blueprints separados para homologacao e producao no Render.
- PostgreSQL gerenciado com acesso publico bloqueado no Blueprint.
- URL PostgreSQL do provedor normalizada para o driver psycopg 3.
- Migracoes e verificacao completa executadas no pre-deploy de producao.
- Health check de prontidao com consulta real ao banco.
- HTTPS externo gerenciado pela plataforma sem redirecionar internamente o health check.
- Criacao idempotente e segura do primeiro administrador, com troca obrigatoria de senha.
- GitHub Actions com testes, Ruff, Bandit, pip-audit e validacao JavaScript/YAML.
- Dependabot semanal para dependencias Python e GitHub Actions.
- Leaflet 1.9.4 fixado com Subresource Integrity (SRI); qualquer arquivo divergente e rejeitado pelo navegador.
- Teste online nao destrutivo para HTTPS, cabecalhos, banco, login, sessao e logout.
- Corrigida uma condicao duplicada que impediria o preflight de producao de compilar.

## 0.1.4.1

- Corrigido o bloqueio 403 dos tiles do OpenStreetMap no monitor de rastreamento.
- Ajustado o cabeçalho Referrer-Policy somente na página de rastreamento, sem expor caminhos ou parâmetros a terceiros.
- Atualizada a URL oficial de tiles e a política CSP.

## 0.1.4 — Security Hardened

- Limite persistente de tentativas: terceira falha bloqueia por 30 segundos, com progressão até 300 segundos.
- Limite adicional por IP e proteção da reautenticação para troca de senha.
- Mensagens genéricas de autenticação e hash fictício para reduzir enumeração por tempo.
- Cookies HttpOnly, access token curto, refresh opaco rotativo e revogação persistida.
- CSRF assinado, validação de origem e cabeçalhos de segurança.
- Troca obrigatória de senha e invalidação de sessões em mudanças sensíveis.
- Alteração da própria senha exige reautenticação; o cadastro administrativo não pode contornar essa confirmação.
- Preflight de produção, `.env.production.example` e scripts de execução endurecida; `--config-only` funciona antes da conexão com PostgreSQL.
- Limite de corpo, validação de entrada e sanitização de erros.
- Rotação de logs, backup e scripts de análise automatizada.
- Migrações `0003_security` e `0004_sessions`.

## 0.1.3

- Rastreamento GPS e monitor administrativo.
- Uma rota em andamento por motorista/veículo.

## 0.1.2

- Aplicativo web mobile do motorista.

## 0.1.1

- Sincronização e idempotência de status de rota.

## 1.0.0-rc1.2 - 2026-10-21

### Segurança

- Atualizado `PyJWT` de `2.13.0` para `2.15.1` para corrigir os alertas identificados pelo `pip-audit` no pipeline de produção.
- Mantido o uso explícito de algoritmo, emissor, público e claims obrigatórias na validação dos tokens JWT.

### Qualidade

- Adicionada validação específica de emissão e leitura de tokens após a atualização da dependência.
