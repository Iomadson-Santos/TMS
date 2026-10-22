# Segurança do TMS — versão 0.1.4.1

Este documento descreve os controles implementados no código. Ele não afirma que o sistema é invulnerável e não substitui avaliação de infraestrutura, teste de invasão ou monitoramento contínuo.

## Autenticação e bloqueio temporário

O backend mantém contadores persistentes em forma de HMAC; o e-mail e o IP originais não são armazenados na tabela de limitação.

Valores padrão:

```env
LOGIN_MAX_ATTEMPTS=3
LOGIN_IP_MAX_ATTEMPTS=20
LOGIN_LOCK_SECONDS=30
LOGIN_LOCK_MAX_SECONDS=300
LOGIN_ATTEMPT_WINDOW_SECONDS=900
```

Na terceira senha incorreta, o identificador é bloqueado por 30 segundos. Novas sequências de três erros na mesma janela dobram o prazo até 300 segundos. O servidor retorna `429 Too Many Requests` e o cabeçalho `Retry-After`.

Existe também um contador por IP. Ele reduz ataques distribuídos contra várias contas sem depender apenas do bloqueio de uma conta específica. Uma autenticação correta limpa os contadores associados àquele login e IP.

A confirmação da senha atual em `/auth/change-password` recebe o mesmo bloqueio após três erros dentro da sessão.

As respostas são genéricas:

```text
E-mail ou senha inválidos
```

Assim, o endpoint não informa se a conta existe, está inativa ou apenas teve a senha digitada incorretamente.

## Senhas

- Hash Argon2id por meio de `pwdlib`.
- Comprimento local mínimo de 12; produção exige no mínimo 15 pelo preflight.
- Máximo de 128 caracteres para limitar consumo indevido no Argon2.
- Rejeição de senhas conhecidas, previsíveis, iguais às demonstrações ou que contenham o e-mail/nome completo.
- Novos usuários recebem senha temporária e precisam alterá-la no primeiro acesso.
- A migração marca contas antigas para troca porque não é possível avaliar uma senha original a partir do hash.
- Trocar senha incrementa `auth_version` e revoga todas as sessões.
- O administrador não pode redefinir a própria senha pelo cadastro de usuários; precisa confirmar a senha atual na tela **Trocar senha**, que também possui bloqueio progressivo.

O projeto não consulta ainda uma base online de senhas vazadas e não possui MFA. Esses dois itens permanecem recomendados para uma etapa posterior.

## Sessões e tokens

### Navegador

- Access token JWT com emissor, audiência, tipo, JTI, versão da conta e expiração.
- Duração padrão do access token: 15 minutos.
- JWT armazenado em cookie `HttpOnly`, não em `localStorage`.
- Refresh token opaco e aleatório; o banco guarda apenas um HMAC.
- Refresh rotativo. Reutilização fora da pequena janela de concorrência revoga a família da sessão.
- Sessão com expiração absoluta de 7 dias e inatividade padrão de 12 horas.
- Limite padrão de cinco sessões por usuário; a mais antiga é revogada ao exceder.
- Logout, logout global e revogação individual de sessão.
- Alterar senha, e-mail, perfil ou situação do usuário invalida credenciais anteriores.

### Integrações

O endpoint Bearer `/auth/token` pode ser usado no desenvolvimento, mas vem desativado no modelo de produção. Caso uma integração futura precise dele, deve haver aprovação específica, segredo próprio, escopo limitado e rotação.

## CSRF, origem e CORS

Operações `POST`, `PUT`, `PATCH` e `DELETE` autenticadas por cookie exigem um token CSRF assinado e vinculado ao ID da sessão. O valor precisa existir tanto no cookie legível pelo frontend quanto no cabeçalho `X-CSRF-Token`.

O middleware também rejeita `Sec-Fetch-Site: cross-site` e valida `Origin`/`Referer` quando presentes. Em produção, `CORS_ORIGINS`, `PUBLIC_BASE_URL` e `ALLOWED_HOSTS` precisam conter somente o domínio oficial.

## Autorização

As regras são validadas no backend:

- Administrador: usuários, auditoria, exclusões e operação completa.
- Operador: veículos, entregas, rotas, dashboard e monitor de rastreamento.
- Motorista: somente as rotas atribuídas ao próprio ID, suas entregas e seu histórico de GPS.
- Motorista não acessa usuários, auditoria, dashboard, lista geral de veículos ou monitor administrativo.
- Motorista não pode cancelar rota nem alterar campos de entrega além de `entregue`/`devolvida` durante a própria rota em andamento.
- Banco e aplicação impedem duas rotas simultâneas para o mesmo motorista ou veículo.

Esconder botões na interface não é considerado controle de acesso; cada endpoint possui dependência de perfil e, quando necessário, verificação do objeto solicitado.

## Navegador e conteúdo

As respostas recebem:

- `Content-Security-Policy`;
- `X-Frame-Options: DENY`;
- `X-Content-Type-Options: nosniff`;
- `Referrer-Policy: no-referrer` por padrão e `strict-origin-when-cross-origin` apenas na página de rastreamento, para cumprir a política do provedor de mapas sem expor caminhos ou parâmetros;
- `Permissions-Policy`;
- `Cross-Origin-Opener-Policy`;
- `Cross-Origin-Resource-Policy`;
- `Strict-Transport-Security` somente com HTTPS habilitado;
- `Cache-Control: no-store` para páginas e API.

Dados inseridos pelo usuário são escapados antes de entrar em templates HTML dinâmicos. Pydantic rejeita campos desconhecidos e os handlers de erro não ecoam os valores recebidos.

O mapa usa o endpoint oficial atual de tiles do OpenStreetMap, envia apenas a origem como referência para cumprir a política do provedor e mantém a atribuição visível. O Leaflet ainda é carregado de `unpkg.com` com integridade SRI. Uma evolução de maior isolamento é hospedar essa dependência dentro do próprio domínio.

## Proteção de recursos

- Corpo de requisição limitado a 1 MiB por padrão, inclusive transferências em partes.
- Limite de 500 entregas por operação de rota/otimização.
- Limite de 5.000 posições por consulta de histórico.
- GPS aceita no máximo um ponto a cada dois segundos por motorista/rota.
- Campos textuais, números e coordenadas possuem limites de tamanho/faixa.

As listagens administrativas ainda retornam coleções sem paginação completa. Para bases muito grandes, paginação com cursor deve ser adicionada antes de escalar o número de registros.

## Auditoria e logs

A auditoria registra usuário, ação, entidade, horário, IP e detalhes sem incluir senha, token ou cookie. Eventos de segurança incluem:

- `login`, `login_failed`, `login_locked`;
- `refresh_failed`, `refresh_stale`, `refresh_reuse`;
- `logout`, `logout_all`, `session_revoke`;
- `password_change_failed`, `password_change_locked`, `password_change`;
- alteração de conta e operações do TMS.

Os logs de aplicação usam rotação por tamanho. Em produção, proteja a pasta contra leitura por outros usuários do sistema, encaminhe alertas importantes para monitoramento e defina retenção conforme a política da empresa.

## Preflight de produção

`python -m app.scripts.security_check` bloqueia a publicação quando encontra, entre outros:

- ambiente diferente de `production`;
- segredo fraco ou padrão;
- SQLite;
- criação automática de tabelas;
- seed/administrador automático habilitados;
- cookies sem `Secure` ou sem prefixo `__Host-`;
- documentação e endpoint de token habilitados;
- domínio, CORS, host ou HTTPS inseguros;
- política de senha insuficiente;
- conta de demonstração ainda usando senha pública;
- ausência de administrador ou migrações.

O servidor também executa a validação de configuração no startup e se recusa a iniciar com parâmetros perigosos.

## Itens que ainda exigem processo operacional

- HTTPS real em proxy reverso e renovação automática do certificado.
- PostgreSQL com usuário de privilégio mínimo e acesso de rede restrito.
- backups automáticos, cópia externa e teste de restauração.
- atualização regular do sistema operacional e das dependências.
- varredura de dependências em ambiente conectado imediatamente antes do deploy.
- teste de invasão independente, especialmente antes de expor dados pessoais e GPS.
- política de privacidade, retenção e acesso aos dados de localização.
- MFA para administradores e operadores em uma próxima versão.
