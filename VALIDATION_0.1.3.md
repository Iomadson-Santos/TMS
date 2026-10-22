# Validacao da versao 0.1.3

Foram executados os seguintes testes:

- compilacao de todos os modulos Python;
- verificacao de sintaxe de todos os arquivos JavaScript;
- migracao de um banco SQLite vazio ate `0002_tracking`;
- atualizacao de um banco legado 0.1.2 criado sem `alembic_version`;
- criacao da tabela e dos indices de rastreamento;
- login como administrador, operador e dois motoristas diferentes;
- confirmacao de que cada motorista recebe somente as proprias rotas;
- bloqueio `403 Forbidden` para dashboard, lista geral de veiculos e seletor de motoristas quando o usuario e motorista;
- inicio de uma rota pelo proprio motorista;
- bloqueio da tentativa de cancelamento pelo motorista, mantendo o cancelamento com administrador/operador;
- bloqueio `409 Conflict` ao iniciar uma segunda rota para o mesmo motorista;
- registro de uma posicao GPS pelo motorista responsavel;
- bloqueio `403 Forbidden` quando outro motorista tenta enviar posicao para a rota;
- consulta do monitor por administrador e operador;
- bloqueio do monitor para o perfil motorista;
- consulta do historico pelo motorista responsavel;
- bloqueio do historico para outro motorista;
- autenticacao e conexao inicial do WebSocket do monitor;
- abertura das rotas HTTP `/tracking` e `/motorista`.

Resultado: aprovado no ambiente de teste SQLite. O GPS real depende de permissao do navegador e HTTPS no celular.
