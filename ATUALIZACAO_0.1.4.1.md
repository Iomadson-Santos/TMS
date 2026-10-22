# Atualização 0.1.4.1 — correção do mapa de rastreamento

Esta atualização corrige o erro `403 Access blocked` exibido nos blocos do mapa.

## Causa

A versão 0.1.4 aplicava `Referrer-Policy: no-referrer`, enquanto o serviço público de tiles do OpenStreetMap exige que aplicações web enviem um cabeçalho `Referer` válido. O código também utilizava o formato antigo com subdomínios (`{s}.tile.openstreetmap.org`).

## Correções

- `Referrer-Policy` mantido como `no-referrer` no restante do sistema e alterado para `strict-origin-when-cross-origin` somente em `/tracking`;
- URL dos tiles alterada para `https://tile.openstreetmap.org/{z}/{x}/{y}.png`;
- CSP atualizada para permitir apenas o endpoint oficial;
- carregamento de tiles reduzido durante movimentação do mapa;
- aviso de indisponibilidade exibido quando o provedor falhar;
- cache-busting do JavaScript do rastreamento.

## Instalação

1. Pare o servidor com `Ctrl + C`.
2. Extraia o ZIP sobre a pasta que contém o projeto e confirme a substituição dos arquivos.
3. Execute `run_windows.bat`.
4. Abra `/tracking` e pressione `Ctrl + F5` uma vez.

Não há alteração de banco, dependências ou arquivos `.env`.
