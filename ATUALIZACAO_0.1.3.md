# Atualizacao 0.1.3 - rota unica e rastreamento GPS

Esta atualizacao foi preparada para ser aplicada sobre a versao 0.1.2 sem apagar o ambiente virtual, o arquivo `.env` ou o banco `backend/tms.db`.

## O que muda

- cada motorista continua visualizando somente as rotas atribuidas ao proprio usuario e pode apenas iniciar/concluir a propria viagem;
- endpoints administrativos de dashboard, usuarios, frota geral e monitor continuam bloqueados para o perfil motorista;
- um motorista nao pode ter duas rotas em andamento ao mesmo tempo;
- um veiculo nao pode estar em duas rotas em andamento ao mesmo tempo;
- a tela de rotas bloqueia o botao de inicio quando o motorista ou o veiculo ja esta em viagem;
- o aplicativo mobile passa a compartilhar o GPS somente durante uma rota em andamento;
- administradores e operadores recebem a pagina `/tracking` com mapa, sinal online/offline, velocidade, precisao, progresso e historico do trajeto;
- atualizacao em tempo real por WebSocket, com consulta automatica de contingencia a cada 15 segundos;
- pontos de rastreamento mais antigos que o periodo configurado sao removidos gradualmente. O padrao e 90 dias.

## Como instalar no Windows

1. Pare o servidor com `Ctrl + C`.
2. Extraia o ZIP de atualizacao na pasta que contem `tms_ciranda_starter`.
3. Confirme a substituicao dos arquivos.
4. Abra a pasta do projeto e execute:

```bat
update_windows.bat
```

5. Depois execute:

```bat
run_windows.bat
```

6. Abra `http://127.0.0.1:8000` e pressione `Ctrl + F5`.

A atualizacao cria a tabela `tracking_positions` e dois bloqueios de banco para impedir rotas simultaneas do mesmo motorista ou veiculo. Por isso, o `update_windows.bat` deve ser executado uma vez.

## Dados preservados

O pacote de atualizacao nao inclui e nao remove:

```text
.venv/
backend/.env
backend/tms.db
```

## Teste recomendado

1. Entre como administrador.
2. Crie dois usuarios com perfil Motorista.
3. Crie uma rota para cada motorista.
4. Inicie uma rota.
5. Entre com o motorista pelo endereco `/motorista` e permita o acesso a localizacao.
6. Entre como administrador ou operador e abra `/tracking`.
7. Tente iniciar uma segunda rota para o mesmo motorista. O sistema deve bloquear a operacao.

## Aviso sobre GPS no celular

A maioria dos navegadores permite geolocalizacao apenas em contexto seguro. `localhost` funciona no computador, mas o endereco `http://IP_DO_COMPUTADOR:8000` normalmente nao libera GPS no celular. Para rastreamento real, publique o TMS com HTTPS ou use um certificado confiavel. Consulte `RASTREAMENTO.md`.
