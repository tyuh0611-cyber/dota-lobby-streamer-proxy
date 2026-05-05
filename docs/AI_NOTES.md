# AI notes — streamer proxy repository

These notes are for future ChatGPT/AI work on this repo.

## Rule: keep notes updated

Whenever streamer setup, OAuth, deployment, or Dota/Steam strategy changes, update this file or `docs/project_context.md`.

Whenever files are added/removed/moved, update `PROJECT_FILES.txt`.

Do not leave important decisions only in chat history.

## Current split

This repo is streamer-proxy only. Backend code belongs in:

```text
tyuh0611-cyber/dota-lobby-backend
```

Old monorepo was:

```text
tyuh0611-cyber/dota-twitch-lobby-bot
```

## Streamer proxy responsibilities

- Twitch OAuth auth URL
- Twitch callback
- token storage in local `.env`
- Twitch chatters endpoint
- Dota lobby status endpoint
- Dota invite endpoint
- future real Steam/Dota Game Coordinator adapter

## Not streamer proxy responsibilities

- PostgreSQL player DB
- web dashboard UI
- queue ranking logic
- backend user/session auth

## Important decisions already made

- Streamer should not manually search for Twitch broadcaster/moderator numeric IDs.
- Setup should ask for Client ID / Client Secret and public base URL.
- OAuth should later resolve and store numeric Twitch IDs automatically.
- `PUBLIC_BASE_URL` exists to avoid Twitch redirect mismatch with localhost.
- Real secrets stay in local `.env`; examples and docs only go to Git.

## Current known issue/focus

Twitch auth URL previously generated:

```text
http://localhost:8081/twitch/callback
```

It must generate:

```text
https://test.raze1x6.mom/twitch/callback
```

using:

```env
PUBLIC_BASE_URL=https://test.raze1x6.mom
```

## Future setup goal

Create installer/setup script that asks:

```text
Public base URL
Proxy API key or auto-generate
Twitch Client ID
Twitch Client Secret
Dota mock mode
```

and writes local `.env` safely.
