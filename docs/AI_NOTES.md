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
- real Steam/Dota Game Coordinator adapter

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

## Dota/Steam notes as of 2026-05-07

The current real Dota blocker is lobby shared-object detection, not Steam login.

Already verified before 2026-05-07:

- Steam login works.
- Steam Guard one-time code works.
- `Dota2Client.launch()` works.
- `wait_event('ready')` works.
- `/dota/status` can show `connected=true`, `gc_started=true`, `real_adapter_ready=true`.
- `/dota/create-lobby` exists.
- `create_practice_lobby()` sends a message but previously did not produce `lobby_new` / `lobby_changed`.
- `invite_to_lobby()` silently returns if `self._dota.lobby is None`, so invite testing must wait until `lobby_detected=true`.

Important patch pushed on 2026-05-07:

```text
4c73b102bb05bf420fb6e6989f95c09e0c231c9c Keep Dota GC operations on one gevent worker
```

Reason:

The `steam`/`dota2` libraries use gevent internally. The old implementation used separate `asyncio.to_thread(...)` calls, so Steam login / Dota launch / lobby creation / invite could run on different worker threads and different gevent hubs. That can prevent SOCache updates from being observed reliably.

Current implementation uses one persistent `ThreadPoolExecutor(max_workers=1, thread_name_prefix='dota-gevent')` and routes all real Steam/Dota operations through `_run_sync(...)`.

Deployment verification:

```bash
curl -s -H "X-Api-Key: $KEY" http://127.0.0.1:8081/dota/status
```

Expected flag after deploy:

```text
"dota_worker":"single_thread_gevent_executor"
```

Only test `/dota/invite` after `/dota/status` or `/dota/create-lobby` shows:

```text
lobby_detected=true
```

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
