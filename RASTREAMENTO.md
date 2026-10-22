# Rastreamento do motorista

## Funcionamento

O aplicativo do motorista usa a API de geolocalizacao do navegador. Quando a rota passa para `em_andamento`, a tela solicita permissao para acessar o GPS e envia pontos para:

```text
POST /api/v1/tracking/positions
```

O backend valida o token, confirma que o usuario possui perfil `motorista`, confirma que a rota pertence a esse usuario e aceita a posicao somente enquanto a rota estiver em andamento.

Administradores e operadores acompanham as viagens em:

```text
/tracking
```

O monitor usa WebSocket para receber avisos de novas posicoes e faz uma consulta de contingencia a cada 15 segundos. O mapa e carregado com Leaflet e OpenStreetMap.

## Permissoes

- Administrador: visualiza todas as rotas em andamento e seus historicos.
- Operador: visualiza todas as rotas em andamento e seus historicos.
- Motorista: visualiza somente as proprias rotas, pode apenas iniciar/concluir a propria viagem, envia localizacao somente para a rota em andamento e consulta apenas o proprio historico.
- Um motorista nao consegue enviar GPS para a rota de outro usuario, mesmo alterando manualmente a requisicao.

## Quando o motorista e considerado online

O padrao e considerar o GPS online quando o servidor recebeu uma posicao nos ultimos 120 segundos. Isso pode ser alterado em `backend/.env`:

```env
TRACKING_ONLINE_SECONDS=120
```

## Retencao dos pontos

O padrao e manter 90 dias de historico:

```env
TRACKING_RETENTION_DAYS=90
```

Use `0` somente quando houver uma politica definida para manter o historico sem limpeza automatica. Quanto menor o intervalo entre pontos, maior sera o banco.

## HTTPS no celular

A geolocalizacao do navegador normalmente exige HTTPS. O acesso por `http://192.168.x.x:8000` pode abrir a tela, mas o navegador tende a bloquear o GPS.

### Opcao recomendada

Publique o TMS em um servidor com dominio e HTTPS, usando um proxy reverso como Caddy ou Nginx e um certificado valido. Depois o motorista acessa, por exemplo:

```text
https://tms.suaempresa.com.br/motorista
```

### Teste local com certificado

O projeto inclui `run_https_windows.bat`. Ele procura:

```text
certs/server.crt
certs/server.key
```

Os arquivos precisam formar um certificado confiavel para o nome ou IP usado no celular. Uma ferramenta como `mkcert` pode gerar certificados locais, mas a autoridade certificadora local tambem precisa ser confiada pelo aparelho. Exemplo, ajustando o IP para o seu computador:

```bat
mkdir certs
mkcert -install
mkcert -cert-file certs\server.crt -key-file certs\server.key localhost 127.0.0.1 192.168.0.15
run_https_windows.bat
```

Se o IP do computador mudar, gere outro certificado. Nao use certificados privados de producao em computadores pessoais.

## Limitacoes do navegador

- O usuario precisa permitir a localizacao.
- O GPS precisa estar ligado.
- A pagina do motorista deve permanecer aberta.
- Android e iOS podem reduzir ou suspender atualizacoes quando o navegador fica em segundo plano ou a tela e bloqueada.
- Para rastreamento continuo garantido em segundo plano, a evolucao indicada e um aplicativo nativo com politicas de bateria e permissao de localizacao em segundo plano.

## Privacidade e operacao

O sistema envia localizacao somente durante a rota em andamento. Antes de usar em producao, a empresa deve definir e comunicar a finalidade do rastreamento, os perfis autorizados, o periodo de retencao e o procedimento de atendimento ao motorista. Troque as senhas de demonstracao e a `SECRET_KEY` antes da publicacao.
