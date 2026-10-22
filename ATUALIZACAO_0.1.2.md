# Atualização 0.1.2 — aplicativo mobile do motorista

Esta atualização cria uma interface própria para o usuário com perfil `motorista`.

## O que muda

- Após o login, motoristas são enviados automaticamente para `/motorista`.
- O motorista não entra mais nas telas administrativas em formato desktop.
- A tela mobile mostra a rota ativa, o veículo, a data prevista, o progresso e a próxima parada.
- Cada parada possui botão para abrir a navegação no mapa.
- Durante a rota, o motorista pode marcar a entrega como `Entregue` ou `Devolvida`.
- A conclusão da rota é liberada apenas após finalizar todas as paradas.
- A tela sincroniza automaticamente a cada 30 segundos e ao voltar para o aplicativo.
- A página informa se o aparelho está online ou offline.
- Rotas concluídas e canceladas aparecem no histórico recente.

## Instalação sobre a versão 0.1.1

1. Pare o servidor com `Ctrl + C`.
2. Extraia o ZIP de atualização sobre a pasta atual `tms_ciranda_starter`.
3. Confirme a substituição dos arquivos.
4. Execute `run_windows.bat` para testar no computador.
5. Para testar em um celular na mesma rede Wi-Fi, execute `run_mobile_windows.bat`.
6. No navegador, pressione `Ctrl + F5` uma vez para limpar o cache antigo.

Não é necessário executar `setup_windows.bat`, reinstalar bibliotecas ou migrar o banco.

## Acesso de demonstração

```text
E-mail: motorista@tmsciranda.com.br
Senha: Motorista123!
```

## Acesso pelo celular

Ao executar `run_mobile_windows.bat`, o terminal mostra o IPv4 do computador. No celular, use um endereço como:

```text
http://192.168.0.15:8000/motorista
```

O computador e o celular precisam estar na mesma rede Wi-Fi. Quando o Windows solicitar, permita o acesso do Python/Uvicorn em **redes privadas**.
