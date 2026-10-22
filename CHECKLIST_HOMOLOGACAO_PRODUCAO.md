# Checklist de homologacao e liberacao do TMS

Use uma copia para homologacao e outra para producao. Registre data, responsavel e evidencia de cada item.

## Identificacao

```text
Ambiente: [ ] Homologacao  [ ] Producao
URL:
Data:
Responsavel tecnico:
Responsavel operacional:
Versao/commit:
```

## A. Infraestrutura

- [ ] CI do GitHub concluido sem falhas.
- [ ] Deploy concluido sem falhas.
- [ ] Aplicacao responde somente por HTTPS para o usuario.
- [ ] `/api/v1/health/ready` retorna `200` e `database=ok`.
- [ ] PostgreSQL e Web Service estao na mesma regiao.
- [ ] Banco de producao usa plano pago.
- [ ] Banco de producao tem acesso publico bloqueado.
- [ ] Nao existe `.env`, banco, certificado ou backup no repositorio.
- [ ] Logs nao exibem senha, cookie, token ou corpo sensivel.
- [ ] Horario e fuso exibidos estao corretos para a operacao.

## B. Administrador inicial

- [ ] Login inicial funcionou com a senha temporaria.
- [ ] Troca obrigatoria de senha foi exibida.
- [ ] Nova senha possui pelo menos 15 caracteres e e exclusiva.
- [ ] Login com a senha antiga deixou de funcionar.
- [ ] `INITIAL_ADMIN_PASSWORD` foi removida do ambiente apos a troca.
- [ ] Conta administrativa foi registrada na auditoria.

## C. Autenticacao e sessoes

- [ ] Primeira senha errada retorna falha generica.
- [ ] Segunda senha errada retorna falha generica.
- [ ] Terceira senha errada bloqueia por 30 segundos.
- [ ] Durante o bloqueio, nem a senha correta entra.
- [ ] Apos o prazo, a senha correta entra.
- [ ] Logout invalida a sessao.
- [ ] Alteracao de senha invalida as sessoes antigas.
- [ ] Atualizar a pagina nao revela o JWT no `localStorage`.
- [ ] Cookies de sessao usam `Secure`, `HttpOnly` quando aplicavel e `SameSite=Lax`.
- [ ] A pagina nao abre dentro de iframe externo.

## D. Perfis e permissoes

- [ ] Administrador acessa usuarios, auditoria e todos os modulos.
- [ ] Operador acessa somente as funcoes previstas.
- [ ] Motorista e redirecionado para a interface mobile.
- [ ] Motorista A nao lista a rota do Motorista B.
- [ ] Motorista A nao altera uma entrega do Motorista B pela interface.
- [ ] Tentativa direta de API em recurso de outro motorista retorna `403` ou `404` controlado.
- [ ] Motorista nao acessa usuarios, auditoria ou monitor administrativo.
- [ ] Usuario inativo nao consegue autenticar.

## E. Veiculos, entregas e rotas

- [ ] Veiculo ficticio foi cadastrado.
- [ ] Placa duplicada foi rejeitada.
- [ ] Entrega ficticia foi cadastrada.
- [ ] Campos obrigatorios e valores invalidos foram rejeitados.
- [ ] Rota foi criada com veiculo, motorista e entregas.
- [ ] Botao **Iniciar** mudou para status **Em andamento**.
- [ ] Segundo clique nao criou conflito visual nem duplicou inicio.
- [ ] Um motorista nao iniciou duas rotas simultaneas.
- [ ] Um veiculo nao iniciou duas rotas simultaneas.
- [ ] Rota nao foi concluida com entrega pendente.
- [ ] Apos finalizar as paradas, a rota foi concluida.
- [ ] Cancelamento e exclusao obedeceram as regras de status.

## F. Mobile do motorista

- [ ] Tela foi aberta em Android pela URL HTTPS.
- [ ] Layout ficou legivel sem zoom horizontal.
- [ ] Somente a rota atribuida apareceu.
- [ ] Endereco abriu no aplicativo de mapas.
- [ ] Entrega foi marcada como entregue.
- [ ] Devolucao/ocorrencia foi registrada conforme o fluxo atual.
- [ ] Rota concluida apareceu no historico.
- [ ] Com a tela bloqueada ou navegador em segundo plano, a limitacao de GPS foi compreendida e registrada.

## G. Rastreamento, caso seja usado

- [ ] Mapa carregou sem erro 403.
- [ ] Somente administrador e operador acessaram o monitor.
- [ ] Posicao apareceu apenas durante rota em andamento.
- [ ] Ultimo sinal e estado online/offline foram atualizados.
- [ ] WebSocket reconectou depois de uma interrupcao curta.
- [ ] Politica interna de privacidade do GPS foi comunicada aos motoristas.

## H. Auditoria e erros

- [ ] Login com sucesso foi auditado.
- [ ] Falha e bloqueio de login foram auditados.
- [ ] Criacao/alteracao de usuario foi auditada.
- [ ] Criacao e mudanca de status de rota foram auditadas.
- [ ] Erro de validacao nao repetiu senha ou dado secreto.
- [ ] Erro interno retornou mensagem generica e `request_id`.
- [ ] `request_id` correspondente apareceu no log.

## I. Backup e recuperacao

- [ ] Recuperacao point-in-time do banco pago esta disponivel no painel.
- [ ] Export logico foi criado antes da liberacao.
- [ ] Backup foi armazenado fora da conta principal da aplicacao.
- [ ] Procedimento de restauracao esta documentado.
- [ ] Teste de restauracao foi agendado ou executado.
- [ ] Responsavel por backups foi definido.

## J. Teste automatico online

Execute:

```powershell
.\smoke_test_online_windows.bat
```

- [ ] Saude da aplicacao e banco: OK.
- [ ] HTTPS e cabecalhos: OK.
- [ ] Login do administrador: OK.
- [ ] Sessao autenticada: OK.
- [ ] Logout protegido por CSRF: OK.

## K. Liberacao

- [ ] Nenhuma conta usa `Admin123!`, `Operador123!` ou `Motorista123!`.
- [ ] Nao ha dados reais na homologacao gratuita.
- [ ] Senhas temporarias foram removidas das variaveis de ambiente.
- [ ] Custo mensal foi aprovado.
- [ ] Politica de acesso e responsaveis foram definidos.
- [ ] Plano de indisponibilidade e contato de suporte foi comunicado.
- [ ] Responsavel tecnico aprovou.
- [ ] Responsavel operacional aprovou.

## Resultado

```text
[ ] APROVADO PARA USO CONTROLADO
[ ] REPROVADO — CORRECOES NECESSARIAS

Pendencias:

Assinatura tecnica:
Assinatura operacional:
Data:
```
