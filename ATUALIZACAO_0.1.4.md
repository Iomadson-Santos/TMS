# Atualização 0.1.4 — endurecimento de segurança

Esta atualização deve ser aplicada sobre a versão 0.1.3. Ela preserva o banco, o ambiente virtual e as configurações locais, mas altera autenticação e sessões. Por isso, todos os usuários precisarão entrar novamente e trocar a senha no primeiro acesso.

## Antes de começar

Pare o servidor no terminal:

```text
Ctrl + C
```

Como `backup_windows.bat` é adicionado por esta própria atualização, faça primeiro uma cópia manual da pasta atual ou, no mínimo, destes arquivos quando existirem:

```text
backend\.env
backend\tms.db
```

Não apague essa cópia até concluir os testes.

## Instalação no Windows

1. Extraia `tms_atualizacao_seguranca_v0.1.4.zip` na pasta que contém `tms_ciranda_starter`.
2. Confirme **Substituir os arquivos no destino**.
3. Verifique se a estrutura não ficou duplicada:

```text
Área de Trabalho
└── tms_ciranda_starter
    ├── backend
    ├── frontend
    ├── update_windows.bat
    └── run_windows.bat
```

4. Agora que o novo script já está na pasta, crie também um backup consistente do banco:

```bat
backup_windows.bat
```

5. Aplique a atualização:

```bat
update_windows.bat
```

6. Depois execute:

```bat
run_windows.bat
```

7. Abra o sistema e pressione `Ctrl + F5` uma vez.

Não execute `setup_windows.bat` novamente para aplicar esta atualização.

## O que o atualizador faz

- Preserva `.venv`, `backend/.env` e `backend/tms.db`.
- Cria `backend/.env.backup-v0.1.4` antes de alterar o `.env` local.
- Substitui a chave padrão de desenvolvimento por uma `SECRET_KEY` aleatória.
- Reduz `ACCESS_TOKEN_EXPIRE_MINUTES=480` para `15` quando encontra o valor legado.
- Adiciona os parâmetros de login, cookies, sessões, logs e backup que estiverem ausentes.
- Cria as tabelas de limitação de tentativas, tokens revogados e sessões de navegador.
- Adiciona `auth_version` e `must_change_password` aos usuários.
- Marca usuários já existentes para troca obrigatória de senha.

O script não altera automaticamente um `.env` com `ENVIRONMENT=production`; nesse caso ele exige revisão manual.

## Comportamento após atualizar

A primeira autenticação ainda aceita a senha antiga, mas redireciona o usuário para criar uma senha nova. Até concluir a troca, a conta não acessa módulos operacionais.

Após três erros de login:

```text
3 erros → 30 segundos
nova sequência de 3 erros → 60 segundos
nova sequência → 120 segundos
nova sequência → 240 segundos
novas sequências → máximo de 300 segundos
```

O contador progressivo volta ao início após a janela configurada ou após um login correto. O frontend mostra a contagem regressiva, mas o bloqueio real é feito no backend e continua válido mesmo que a página seja recarregada.

## Novas configurações principais

```env
LOGIN_MAX_ATTEMPTS=3
LOGIN_IP_MAX_ATTEMPTS=20
LOGIN_LOCK_SECONDS=30
LOGIN_LOCK_MAX_SECONDS=300
LOGIN_ATTEMPT_WINDOW_SECONDS=900
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
SESSION_IDLE_MINUTES=720
MAX_ACTIVE_SESSIONS_PER_USER=5
MAX_REQUEST_BODY_BYTES=1048576
```

## Problemas possíveis

### O login pede troca de senha

É esperado nesta atualização. Escolha uma senha nova e longa; depois entre novamente.

### Todas as sessões foram encerradas

É esperado quando a `SECRET_KEY` padrão é substituída. Tokens antigos deixam de ser válidos.

### A migração informa e-mails duplicados

Contas que diferem somente por maiúsculas e minúsculas precisam ser corrigidas antes de criar o índice único. Não apague o banco: restaure o backup e corrija os registros com cuidado.

### A página continua exibindo o código antigo

Pressione `Ctrl + F5`. Os arquivos da 0.1.4 usam versão na URL, mas um cache anterior ainda pode permanecer no navegador.
