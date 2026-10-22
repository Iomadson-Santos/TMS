# Validação técnica — TMS 0.1.4.1

Hotfix do mapa de rastreamento.

## Verificações executadas

- compilação dos módulos Python;
- verificação de sintaxe do `tracking.js`;
- 20 testes de segurança aprovados;
- confirmação de `Referrer-Policy: no-referrer` nas páginas e APIs comuns;
- confirmação de `Referrer-Policy: strict-origin-when-cross-origin` apenas em `/tracking`;
- confirmação de CSP permitindo somente `https://tile.openstreetmap.org` para os tiles;
- confirmação da URL oficial atual do OpenStreetMap sem subdomínios.

Não há migração de banco nem nova dependência.
