# Validação técnica — TMS 0.1.4 Security Hardened

Data da execução: **20 de julho de 2026**.

Este relatório registra os testes executados no código entregue. Ele não equivale a certificação de segurança, teste de invasão independente ou aprovação automática para publicação.

## Resultado geral

- Compilação Python: **aprovada**.
- Testes automatizados: **21 aprovados**.
- Sintaxe JavaScript: **14 arquivos aprovados** com `node --check`.
- Migração de banco novo: **0001 → 0004 aprovada**.
- `alembic check`: **nenhuma nova operação detectada**.
- Atualização de banco 0.1.3 com dados: **aprovada sem perda dos registros conferidos**.
- Atualização segura do `.env`: **aprovada**.
- Backup consistente de SQLite: **aprovado**, incluindo `PRAGMA integrity_check`.
- Preflight de produção: configuração insegura **bloqueada** e configuração endurecida **aceita**.
- Inicialização real do Uvicorn e teste HTTP: **aprovados**.
- Varredura local simples de padrões Python de alto risco: **54 arquivos verificados, zero ocorrência encontrada**.

## Cobertura dos 21 testes automatizados

Os testes verificam, entre outros pontos:

1. cabeçalhos de segurança e ausência do cabeçalho `Server`;
2. bloqueio na terceira tentativa incorreta;
3. progressão do bloqueio temporário;
4. limpeza dos contadores após autenticação correta;
5. cookies de sessão `HttpOnly` e CSRF assinado;
6. vínculo do CSRF à sessão correta;
7. rotação concorrente segura do refresh token;
8. detecção de reutilização de refresh token e revogação da sessão;
9. limite de três erros ao confirmar a senha atual;
10. troca obrigatória de senha;
11. criação local de administrador com Argon2 e troca obrigatória;
12. impedimento de redefinição da própria senha sem reautenticação;
13. revogação de Bearer token;
14. possibilidade de desativar o endpoint Bearer;
15. isolamento de rotas e entregas entre motoristas;
16. bloqueio de duas rotas em andamento para o mesmo motorista;
17. erros de validação sem ecoar a senha recebida;
18. validação de origem;
19. limite de corpo da requisição;
20. rejeição de campos desconhecidos e textos obrigatórios vazios;
21. preflight de configuração de produção.

## Migrações

### Banco novo

Um banco SQLite vazio foi atualizado até:

```text
0004_sessions
```

Foram confirmadas as tabelas:

```text
users
vehicles
routes
deliveries
audit_logs
tracking_positions
login_throttles
revoked_tokens
auth_sessions
```

O comando `alembic check` informou:

```text
No new upgrade operations detected.
```

O aviso do SQLite sobre não refletir um índice baseado em expressão é uma limitação conhecida da reflexão do dialeto; o índice `uq_users_email_lower` foi criado e não houve diferença de migração detectada.

### Atualização da versão 0.1.3

Foi criado um banco na revisão `0002_tracking`, carregado com:

```text
3 usuários
3 veículos
8 entregas
```

Depois da atualização para `0004_sessions`, as mesmas quantidades permaneceram e todas as contas antigas receberam:

```text
auth_version = 1
must_change_password = true
```

Também foram criadas as tabelas `login_throttles`, `revoked_tokens` e `auth_sessions`.

## Atualização do ambiente

O teste do atualizador confirmou:

- criação de cópia integral `.env.backup-v0.1.4`;
- substituição da chave padrão por segredo aleatório;
- redução de `ACCESS_TOKEN_EXPIRE_MINUTES` de 480 para 15;
- inclusão de `LOGIN_MAX_ATTEMPTS=3` e demais controles ausentes;
- preservação integral de um `.env` marcado como `production`, exigindo revisão manual.

## Backup

Uma base SQLite com três registros foi copiada pela API de backup nativa do SQLite. O original e a cópia retornaram:

```text
PRAGMA integrity_check = ok
```

Os registros conferidos foram idênticos.

## Teste HTTP real

O Uvicorn foi iniciado em porta local temporária. Foram confirmados:

```text
GET /api/v1/health              200
GET /                            200
POST /api/v1/auth/login erro 1  401
POST /api/v1/auth/login erro 2  401
POST /api/v1/auth/login erro 3  429
Retry-After                     30
```

Também foram conferidos `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, cache desativado e ausência do cabeçalho `Server` quando Uvicorn é iniciado com `--no-server-header`.

## Preflight

O comando `security_check --config-only` retornou código diferente de zero para uma configuração padrão de produção insegura. Uma configuração com HTTPS, PostgreSQL, cookies `Secure`/`__Host-`, segredo forte, seed desativado, hosts e CORS restritos foi aceita.

O modo `--config-only` foi ajustado para não importar o mecanismo de banco antes da hora; isso permite validar as variáveis mesmo antes de instalar o driver PostgreSQL ou conectar ao servidor.

## Ambiente utilizado

A execução disponível usou **Python 3.13.5** e versões compatíveis já instaladas, incluindo SQLAlchemy 2.0.50, Pydantic 2.13.4 e PyJWT 2.13.0. O ambiente não permitiu baixar todas as versões exatas fixadas no `requirements.txt`; portanto, a instalação final ainda deve ser refeita no ambiente de destino com acesso à internet.

## Verificações que ainda precisam ocorrer no ambiente final

Não foram executados neste ambiente:

- `pip-audit` com base de vulnerabilidades atualizada;
- Bandit;
- Ruff;
- migração e teste integrado contra uma instância PostgreSQL real;
- scanner externo de TLS, portas e cabeçalhos;
- teste de invasão independente;
- teste de carga e concorrência em volume de produção;
- validação operacional de backup **e restauração** do PostgreSQL.

Os scripts `setup_security_tools_*` e `security_review_*` foram incluídos para executar Ruff, Bandit e `pip-audit` em uma máquina conectada. Todos esses passos devem ser repetidos na versão exata e no ambiente exato que serão publicados.

## Conclusão

A versão 0.1.4 passou nos testes funcionais e de endurecimento listados, mas **não deve ser considerada pronta para internet apenas por causa deste relatório**. A publicação depende de seguir `DEPLOY_PRODUCTION.md`, usar PostgreSQL e HTTPS reais, remover credenciais de demonstração, executar os scanners atualizados, testar restauração de backup e realizar revisão externa do ambiente.
