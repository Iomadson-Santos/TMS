# Validacao da release 1.0.0-rc1

## Escopo

Esta validacao cobre a preparacao do codigo para homologacao e producao gerenciada. Ela nao equivale a um teste de invasao externo e nao confirma um deploy em uma conta real do Render.

## Resultados executados no ambiente de montagem

- **25 testes Pytest aprovados**.
- Compilacao de `backend/app`, `backend/tests` e `backend/alembic` aprovada.
- Sintaxe de todos os JavaScripts em `frontend/assets/js` aprovada com `node --check`.
- Parse YAML aprovado para `render.yaml`, `render.staging.yaml` e o workflow do GitHub Actions.
- Parse YAML aprovado tambem para `.github/dependabot.yml`.
- Sintaxe Bash aprovada para `start_render.sh` e `predeploy_render.sh`.
- Preflight `security_check --config-only` aprovado com uma configuracao equivalente ao Render.
- Teste do normalizador de URL `postgresql://` para `postgresql+psycopg://` aprovado.
- Teste do health check de banco aprovado.
- Teste da criacao idempotente do primeiro administrador aprovado.
- Inicializacao real do Uvicorn aprovada; `/api/v1/health/ready` retornou `200` com `database=ok` em banco temporario.

## Problemas encontrados e corrigidos

1. Uma condicao duplicada em `production_security_errors()` causaria erro de sintaxe no inicio de producao.
2. O health check poderia receber um redirect HTTPS antes de consultar o banco. Foi adicionado o modo `PLATFORM_HTTPS_ENFORCED`, usado no Render, para deixar o proxy redirecionar publicamente e permitir que o endpoint interno execute a consulta real.
3. A URL PostgreSQL fornecida pelo provedor nao indicava explicitamente o driver psycopg 3. A configuracao agora normaliza o esquema.
4. O Blueprint do banco permitia acesso publico por omissao. Foi definido `ipAllowList: []`.
5. Migracoes eram executadas no start em todos os cenarios. Em producao paga, agora rodam no `preDeployCommand`; a homologacao gratuita continua usando inicializacao idempotente.
6. Faltavam CI e teste online pos-deploy. Ambos foram adicionados.
7. A revisao de dependencias nao tinha atualizacao automatizada. Foi adicionado Dependabot semanal.
8. O carregamento externo do Leaflet permanece fixado na versao 1.9.4 com hashes SRI oficiais; o navegador bloqueia conteudo divergente.

## Verificacoes previstas no CI

O workflow `.github/workflows/ci.yml` executa em um runner com internet:

- Pytest;
- Ruff;
- Bandit;
- `pip-audit`;
- sintaxe JavaScript;
- parse YAML.

Ruff, Bandit e `pip-audit` nao foram executados no ambiente de montagem porque ele nao conseguiu acessar o indice de pacotes para instalar essas ferramentas. O deploy automatico de producao esta configurado como `checksPass`, portanto esses checks devem ser aprovados no GitHub antes de um novo deploy automatico.

## Itens que dependem da conta do usuario

- conectar o GitHub ao Render;
- aprovar recursos e cobranca;
- informar os segredos do administrador inicial;
- executar o primeiro deploy;
- validar a URL publica;
- testar em Android e na rede real;
- configurar dominio corporativo, se aplicavel;
- criar e baixar o primeiro backup logico;
- executar teste externo de seguranca antes de dados sensiveis em escala.

## Conclusao

O codigo esta preparado como **release candidate para homologacao**. A classificacao muda para producao liberada somente depois que o checklist online for concluido e assinado.
