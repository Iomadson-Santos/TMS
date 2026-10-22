# Validação - TMS 1.0.0-rc1.2

## Alteração validada

- `backend/requirements.txt`: `PyJWT==2.13.0` atualizado para `PyJWT==2.15.1`.
- O código do TMS continua usando algoritmo explícito, emissor, público e claims obrigatórias ao decodificar tokens.

## Testes executados

- Compilação de `app`, `tests` e `alembic`: aprovada.
- Testes automatizados do backend: **25 aprovados**.
- Busca no projeto por referências restantes a `PyJWT==2.13.0`: nenhuma ocorrência operacional.
- Estrutura dos arquivos de produção e workflow do GitHub Actions: preservada.

## Confirmação pendente no CI

O ambiente local usado para preparar este patch não possuía acesso de rede ao índice de pacotes para instalar a versão exata e executar o `pip-audit`. A confirmação final da auditoria deve ocorrer automaticamente no GitHub Actions após o push.
