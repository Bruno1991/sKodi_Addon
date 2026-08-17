# Política de segurança, `.env` e dados locais

## `.env`

O `.env` existe apenas na estação de desenvolvimento. Ele não é copiado para add-ons, ZIPs ou GitHub Pages. O runtime Kodi não pode depender dele.

## Credenciais

- GitHub PAT: somente administração/build local; preferir GitHub Actions Secrets.
- Xtream: informado pelo usuário nas configurações do sTv.
- TMDB: configuração dedicada de escopo mínimo; qualquer valor distribuído no cliente é recuperável.
- Cookies/tokens de fonte musical: não publicar, não logar e não sincronizar.

## Sincronização LAN

É proibido transmitir:

- host, usuário ou senha Xtream;
- token TMDB;
- cookies;
- URLs temporárias de mídia;
- conteúdo do `.env`;
- arquivo SQLite completo.

## Logs e diagnóstico

Sanitizar query strings, headers, usernames, paths pessoais e payloads externos. Pacotes de diagnóstico incluem somente versões, capacidades, schemas e logs redigidos.

## Build

O build falha se encontrar `.env`, `.git`, `.db`, `.sqlite`, cookies, logs, `__pycache__`, `.pyc` ou padrões conhecidos de segredo dentro dos add-ons/ZIPs.
