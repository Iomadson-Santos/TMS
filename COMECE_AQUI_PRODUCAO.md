# Comece aqui: publicar e testar o TMS

Release: **1.0.0-rc1**  
Preparada em: **21/10/2026**

Esta e uma release candidate. Primeiro publique a homologacao com dados ficticios. Somente depois crie a producao paga.

## Ordem correta

1. Torne o repositorio `Iomadson-Santos/TMS` privado.
2. Crie a branch `production-v1`.
3. Copie esta release para a branch e confirme que `.env`, `.venv`, bancos, certificados e backups nao entraram no commit.
4. Envie a branch e aguarde o GitHub Actions ficar verde.
5. No Render, crie um Blueprint usando `render.staging.yaml`.
6. Informe nome, e-mail e uma senha temporaria exclusiva para o primeiro administrador.
7. Abra a URL HTTPS, troque a senha e remova `INITIAL_ADMIN_PASSWORD` do ambiente.
8. Execute `smoke_test_online_windows.bat` e o checklist manual.
9. Aprovada a homologacao, crie outro Blueprint usando `render.yaml`.
10. Repita os testes, crie o primeiro backup e somente entao libere usuarios reais.

## Arquivos que devem ser lidos

- `DEPLOY_RENDER_PASSO_A_PASSO.md`: procedimento completo.
- `CHECKLIST_HOMOLOGACAO_PRODUCAO.md`: testes e aceite.
- `VALIDATION_PRODUCTION_RC1.md`: o que foi validado e o que ainda depende do ambiente online.

## Nao faca

- Nao use `run_windows.bat` como servidor publico.
- Nao publique SQLite.
- Nao reutilize `Admin123!`, `Operador123!` ou `Motorista123!`.
- Nao cadastre dados reais na homologacao gratuita.
- Nao exponha a porta interna do Uvicorn.
- Nao avance para producao com CI, smoke test ou checklist em vermelho.
