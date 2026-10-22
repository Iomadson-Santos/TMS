# Correção PyJWT - TMS 1.0.0-rc1.2

A auditoria de dependências do GitHub Actions bloqueou a release porque o projeto fixava `PyJWT==2.13.0`.

## Alteração

O arquivo `backend/requirements.txt` passa a usar:

```text
PyJWT==2.15.1
```

## Instalação no repositório

Extraia o ZIP desta correção diretamente na raiz do repositório `C:\Projetos\TMS`, substitua os arquivos e execute:

```powershell
git add backend/requirements.txt CHANGELOG.md CORRECAO_PYJWT_RC1_2.md RELEASE_MANIFEST_SHA256.txt VALIDATION_PYJWT_RC1_2.md
git commit -m "Atualizar PyJWT para corrigir auditoria"
git push
```

O GitHub Actions será executado novamente automaticamente.
