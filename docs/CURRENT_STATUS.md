# Current status — streamer proxy

Last updated: 2026-05-06

## Repository

Repo:

```text
tyuh0611-cyber/dota-lobby-streamer-proxy
```

This repository owns streamer-side logic:

- Twitch OAuth
- Twitch access/refresh tokens
- Twitch chatters endpoint
- Dota lobby endpoint
- Dota invite endpoint
- future Steam/Dota Game Coordinator integration

Backend UI, database, queue ranking, and Control Center belong in:

```text
tyuh0611-cyber/dota-lobby-backend
```

## Current service path

Systemd should run from:

```ini
WorkingDirectory=/opt/dota-lobby-streamer-proxy
EnvironmentFile=/opt/dota-lobby-streamer-proxy/.env
ExecStart=/opt/dota-lobby-streamer-proxy/.venv/bin/uvicorn app.main:app --host ${APP_HOST} --port ${APP_PORT}
```

## Twitch status

Twitch MVP is complete.

Implemented and verified:

- `/twitch/auth-url`
- HTTPS `/twitch/callback`
- post-auth redirect back to backend Control Center
- access/refresh token persistence
- `/twitch/me`
- `/twitch/setup`
- `/chatters`
- backend Control Center `Status JSON`
- backend login cookie works after OAuth redirect

Notes:

- Twitch `/chat/chatters` is not realtime. Twitch can keep users in chatters for several minutes after they stop watching.
- If `/chatters` returns `503 twitch_token_refreshed_restart_streamer_proxy`, restart `streamer-proxy` so settings reload from `.env`.

## Dota status

Current Dota adapter is still mock, but diagnostics are now explicit.

Implemented streamer endpoints:

```text
/dota/status
/dota/lobby
/dota/invite
```

Current behavior in `DOTA_MOCK_MODE=true`:

- `/dota/status` returns `mode=mock`, `connected=false`, `real_adapter_ready=false`.
- `/dota/lobby` returns a mock lobby with mock members.
- `/dota/invite` returns a mock successful invite response.

Current behavior in `DOTA_MOCK_MODE=false`:

- `/dota/status` returns `mode=real_pending`, `connected=false`, `real_adapter_ready=false`.
- `/dota/lobby` returns HTTP 501 with `real_dota_adapter_not_implemented`.
- `/dota/invite` returns HTTP 501 with `real_dota_adapter_not_implemented`.

This is intentional until real Steam/Dota Game Coordinator integration is implemented.

## Dota env shape

```env
DOTA_MOCK_MODE=true
DOTA_LOBBY_ID=
DOTA_LOBBY_NAME=
DOTA_ACCOUNT_ID=
STEAM_USERNAME=
STEAM_PASSWORD=
STEAM_SHARED_SECRET=
```

Real Steam/Dota credentials stay in local `.env` only and must not be committed.

## First checks after deploy

```bash
cd /opt/dota-lobby-streamer-proxy
python3 -m py_compile app/*.py
systemctl restart streamer-proxy
sleep 2
systemctl status streamer-proxy --no-pager
journalctl -u streamer-proxy -n 80 --no-pager
```

Direct API checks:

```bash
KEY=$(grep '^PROXY_API_KEY=' .env | cut -d= -f2-)
curl -i -H "X-Api-Key: $KEY" http://127.0.0.1:8081/twitch/me
curl -i -H "X-Api-Key: $KEY" http://127.0.0.1:8081/chatters
curl -i -H "X-Api-Key: $KEY" http://127.0.0.1:8081/dota/status
curl -i -H "X-Api-Key: $KEY" http://127.0.0.1:8081/dota/lobby
curl -i -X POST -H "X-Api-Key: $KEY" -H "Content-Type: application/json" -d '{"steam_id":"76561198000000001"}' http://127.0.0.1:8081/dota/invite
```

## Next project step

Next Dota phase:

1. Verify backend Lobby panel and Quick Invite against mock Dota endpoints.
2. Add a safer Dota setup/status panel in backend if needed.
3. Design and implement real Steam/Dota Game Coordinator adapter.

## AI workflow rule

Do not rely only on chat history.

Before work, read from GitHub `main`:

```text
docs/CURRENT_STATUS.md
docs/AI_NOTES.md
docs/project_context.md
PROJECT_FILES.txt
```

After code changes, update docs and push to `main`.
