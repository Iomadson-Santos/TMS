# Publicar o TMS no Render: homologacao e producao

Release: **1.0.0-rc1**  
Data da preparacao: **21/10/2026**

Este roteiro evita colocar dados reais em uma publicacao ainda nao aprovada. A ordem obrigatoria e:

1. enviar a release para uma branch separada no GitHub;
2. publicar uma homologacao temporaria;
3. executar os testes automaticos e manuais;
4. somente depois criar os recursos pagos de producao.

## Arquitetura preparada

- um Web Service Python/FastAPI;
- um PostgreSQL gerenciado na mesma regiao;
- HTTPS terminado no proxy do Render;
- cookies seguros e HSTS;
- migracoes Alembic antes do deploy de producao;
- health check que executa `SELECT 1` no banco;
- uma unica instancia do web service nesta versao;
- CI no GitHub Actions antes de novos deploys automaticos.

A unica instancia e intencional: o monitor de rastreamento usa um hub WebSocket em memoria. Antes de escalar horizontalmente, o hub precisa ser migrado para Redis/Render Key Value ou outro mecanismo de pub/sub.

## 1. Preparar o GitHub

> **Atencao:** em 21/10/2026, o repositorio `Iomadson-Santos/TMS` aparecia como publico. Altere a visibilidade para **privado** antes de enviar esta release ou criar os ambientes do Render.

O repositorio do TMS deve ser **privado**, pois e um sistema interno. O codigo nao contem `.env`, banco SQLite ou certificados no ZIP, e o `.gitignore` tambem bloqueia esses arquivos, mas manter o repositorio privado reduz exposicao operacional.

### Opcao mais simples: GitHub Desktop

1. Clone o repositorio `Iomadson-Santos/TMS` pelo GitHub Desktop.
2. Crie uma branch chamada:

```text
production-v1
```

3. Copie todo o conteudo desta pasta de release para a pasta clonada, substituindo os arquivos antigos.
4. Remova arquivos antigos que nao fazem parte da release, como configuracoes de deploy legadas, caso ainda existam.
5. Confirme que **nao** aparecem no commit:

```text
backend/.env
backend/tms.db
.venv/
certs/
*.pem
backups/
```

6. Crie o commit:

```text
release: TMS 1.0.0-rc1 para homologacao
```

7. Publique a branch `production-v1`.

### Opcao por terminal

Na pasta extraida da release:

```powershell
git init
git checkout -b production-v1
git remote add origin https://github.com/Iomadson-Santos/TMS.git
git add -A
git status
git commit -m "release: TMS 1.0.0-rc1 para homologacao"
git push -u origin production-v1
```

Antes do `commit`, revise o resultado de `git status`. Nao continue se houver `.env`, `.db`, `.venv`, certificados ou backups.

## 2. Confirmar o CI do GitHub

A branch inclui:

```text
.github/workflows/ci.yml
```

No GitHub, abra **Actions** e aguarde o workflow **TMS - qualidade e seguranca**. Ele precisa ficar verde antes de continuar. O workflow executa:

- compilacao Python;
- 25 testes automatizados;
- Ruff;
- Bandit;
- `pip-audit`;
- verificacao dos JavaScripts;
- parse dos arquivos YAML.

Se algum passo falhar, nao publique. Abra o log da etapa, corrija a causa e envie outro commit.

## 3. Criar a homologacao temporaria

A homologacao usa os planos gratuitos apenas para validar a publicacao. **Nao cadastre dados reais nela.**

1. Entre no painel do Render.
2. Selecione **New > Blueprint**.
3. Conecte o GitHub e escolha o repositorio do TMS.
4. Selecione a branch:

```text
production-v1
```

5. Informe o caminho do Blueprint:

```text
render.staging.yaml
```

6. O Render solicitara tres valores secretos. Preencha:

```text
INITIAL_ADMIN_NAME=nome do responsavel
INITIAL_ADMIN_EMAIL=e-mail real do responsavel
INITIAL_ADMIN_PASSWORD=senha temporaria exclusiva com pelo menos 15 caracteres
```

A senha temporaria nao pode conter o nome completo, o inicio do e-mail ou uma das senhas de demonstracao. Guarde-a em um gerenciador de senhas.

7. Confirme a criacao dos dois recursos:

```text
tms-ciranda-homolog
tms-ciranda-homolog-db
```

8. Acompanhe os logs. O inicio esperado inclui, nesta ordem:

```text
Verificacao de seguranca aprovada
Banco de dados atualizado
Administrador inicial preparado
Uvicorn iniciado
```

9. Abra a URL HTTPS exibida pelo Render.

Na homologacao gratuita, o banco expira em 30 dias, nao possui backups e o web service pode adormecer por inatividade. Por isso, ela serve somente para teste temporario.

## 4. Primeiro acesso na homologacao

Entre com o e-mail e a senha temporaria definidos no Blueprint. O sistema exigira uma nova senha no primeiro acesso.

Depois da troca:

1. confirme que o Dashboard abre;
2. confirme que o menu respeita o perfil administrador;
3. saia e entre novamente com a nova senha;
4. no Render, remova a variavel `INITIAL_ADMIN_PASSWORD` do Web Service de homologacao.

A remocao e segura porque o script de inicializacao nao precisa desse valor quando ja existe um administrador ativo.

## 5. Executar o teste automatico online

No computador, abra a pasta desta release e execute:

```powershell
.\smoke_test_online_windows.bat
```

Informe a URL HTTPS da homologacao e as credenciais do administrador quando solicitado. A senha nao aparece no terminal.

O teste valida:

- health check e conectividade PostgreSQL;
- HTTPS e cabecalhos de seguranca;
- login;
- cookie de sessao;
- endpoint `/auth/me`;
- CSRF e logout.

O resultado precisa terminar com:

```text
Publicacao aprovada nos testes automaticos nao destrutivos.
```

## 6. Testes manuais de homologacao

Siga integralmente o arquivo:

```text
CHECKLIST_HOMOLOGACAO_PRODUCAO.md
```

Use somente dados ficticios. Teste no minimo:

- tres senhas incorretas e bloqueio temporario;
- criacao de operador e motorista;
- isolamento das rotas por motorista;
- cadastro de veiculo e entrega;
- criacao, inicio e conclusao da rota;
- tela mobile;
- auditoria;
- mapa;
- logout e expiracao de sessao.

## 7. Criar a producao

Somente continue quando o checklist de homologacao estiver aprovado.

1. No Render, crie outro Blueprint para o mesmo repositorio e branch.
2. Use o arquivo:

```text
render.yaml
```

3. Revise os recursos antes de confirmar. Esse Blueprint usa planos pagos:

```text
Web Service: 0.5 CPU / 512 MB
PostgreSQL: 0.5 CPU / 1 GB, disco inicial de 15 GB
```

O Render mostrara os valores vigentes antes da confirmacao. A cobranca deve ser aprovada pelo responsavel da empresa.

4. Preencha novamente os tres valores do administrador inicial. Use uma senha temporaria diferente da homologacao.
5. Confirme o deploy.

Em producao:

- o banco nao aceita conexoes publicas (`ipAllowList: []`);
- o Web Service usa a conexao privada do banco;
- migracoes e verificacoes de seguranca rodam no `preDeployCommand`;
- se o pre-deploy falhar, a nova versao nao entra em operacao;
- o deploy automatico ocorre somente depois que os checks do GitHub passam.

## 8. Aprovar o primeiro deploy de producao

1. Abra a URL HTTPS `onrender.com` do Web Service.
2. Entre com a senha temporaria.
3. Defina a senha definitiva.
4. Remova `INITIAL_ADMIN_PASSWORD` das variaveis do Web Service.
5. Execute `smoke_test_online_windows.bat` contra a URL de producao.
6. Execute novamente o checklist manual, usando um conjunto pequeno de dados controlados.
7. Crie um backup logico pelo painel do banco e registre quem o baixou e onde foi armazenado.

Somente depois disso libere os demais usuarios.

## 9. Dominio proprio, opcional

A URL `onrender.com` ja usa HTTPS. Para adicionar um dominio corporativo:

1. adicione o dominio nas configuracoes do Web Service;
2. ajuste o DNS conforme o painel;
3. aguarde a validacao do certificado;
4. altere estas variaveis no Web Service:

```text
PUBLIC_BASE_URL=https://tms.seudominio.com.br
ALLOWED_HOSTS=tms.seudominio.com.br,SEU_SERVICO.onrender.com
CORS_ORIGINS=https://tms.seudominio.com.br,https://SEU_SERVICO.onrender.com
```

5. faca um novo deploy;
6. execute o teste online com o dominio novo;
7. somente depois, se desejado, desative o subdominio `onrender.com`.

## 10. Recuperar senha do administrador em producao

Em um Web Service pago, abra a pagina **Shell** do servico no Render e execute:

```bash
cd backend
python -m app.scripts.reset_admin_password
```

O comando solicita a nova senha sem exibi-la, revoga as sessoes e limpa o bloqueio da conta. Use esse procedimento apenas por uma pessoa autorizada e registre a ocorrencia.

## 11. Backup e restauracao

O PostgreSQL pago possui recuperacao point-in-time gerenciada. Isso nao substitui uma copia externa:

- crie um export logico antes de toda migracao relevante;
- mantenha copias periodicas fora do Render;
- teste a restauracao trimestralmente;
- documente RPO, RTO, responsavel e local de armazenamento.

## 12. Limitacoes conhecidas desta release

- uma instancia web apenas, por causa do WebSocket de rastreamento em memoria;
- recuperacao por e-mail ainda nao foi implementada; o reset seguro e feito pelo Shell;
- o mapa depende dos tiles publicos do OpenStreetMap e deve respeitar a politica do provedor;
- a homologacao gratuita nao e duravel;
- esta e uma release candidate: a aprovacao final depende do teste no ambiente real.

## 13. Criterio de liberacao

A producao so deve ser considerada liberada quando:

```text
CI verde
Deploy verde
Smoke test verde
Checklist manual assinado
Senha temporaria removida
Backup criado e restauracao documentada
Usuarios de demonstracao inexistentes
Sem dados reais na homologacao
```
