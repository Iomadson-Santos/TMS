# Atualização 0.1.1 — tela de rotas

Esta atualização corrige os dois comportamentos observados durante os testes:

1. **Rota já iniciada ainda mostrava o botão “Iniciar”**
   - A linha agora é atualizada imediatamente após a resposta da API.
   - Rotas em andamento mostram **“✓ Iniciada”** e o botão **“Concluir”**.
   - O botão clicado fica bloqueado durante a requisição, evitando clique duplo.
   - O backend trata a repetição do mesmo status de forma idempotente; iniciar novamente uma rota já iniciada não gera conflito nem reinicia o horário.

2. **Atualização da página mostrava erro de permissão**
   - A atualização principal consulta apenas rotas e veículos.
   - A lista de motoristas foi movida para um endpoint próprio, que retorna apenas ID e nome para usuários autenticados.
   - Uma falha nos dados auxiliares do formulário não impede mais a atualização da tabela de rotas.
   - A verificação de perfis no backend foi normalizada para aceitar corretamente valores de enumeração e strings persistidas.

## Como aplicar no projeto que já está instalado

1. Pare o servidor com `Ctrl + C`.
2. Faça uma cópia da pasta atual como segurança.
3. Extraia o ZIP desta versão sobre a pasta `tms_ciranda_starter` e confirme a substituição dos arquivos.
4. Não apague `.venv`, `backend/.env` ou `backend/tms.db`.
5. Inicie novamente com `run_windows.bat`.
6. Na página de rotas, pressione `Ctrl + F5` uma vez para limpar o JavaScript antigo do navegador.

Não há alteração na estrutura do banco de dados, portanto não é necessário executar uma nova migração.
