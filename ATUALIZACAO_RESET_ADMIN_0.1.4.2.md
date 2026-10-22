# Reset emergencial de senha do administrador - TMS v0.1.4.2

Esta atualizacao adiciona um reset local e seguro para contas de administrador.

## Protecoes aplicadas

- a senha e digitada de forma oculta;
- a senha nao vai para o historico do terminal;
- a politica de senha do TMS e validada;
- um backup consistente do banco e criado antes da alteracao;
- todas as sessoes do administrador sao revogadas;
- a versao de autenticacao e incrementada, invalidando tokens antigos;
- o bloqueio de login da conta e removido;
- bloqueios locais de 127.0.0.1 e ::1 sao removidos;
- o reset e registrado na auditoria, sem armazenar a senha.

## Instalacao

Extraia o ZIP diretamente dentro da pasta principal do TMS. A estrutura deve ficar:

```text
tms_ciranda_starter_v0.1.4
|-- backend
|   `-- app
|       `-- scripts
|           `-- reset_admin_password.py
|-- reset_admin_password_windows.bat
`-- run_windows.bat
```

Nao e necessario executar setup_windows.bat ou update_windows.bat.

## Uso

1. Pare o servidor com `Ctrl + C`.
2. Execute `reset_admin_password_windows.bat`.
3. Confirme o e-mail do administrador.
4. Digite e confirme uma nova senha forte.
5. Responda se deseja exigir outra troca no proximo login.
6. Execute `run_windows.bat`.

O e-mail padrao sugerido e `admin@tmsciranda.com.br`.
