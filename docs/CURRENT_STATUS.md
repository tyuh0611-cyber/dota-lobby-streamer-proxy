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
- Steam/Dota Game Coordinator integration

Backend UI, database, queue ranking, and Control Center belong in:

```text
tyuh0611-cyber/dota-lobby-backend
```

## Current service path

Systemd unit shows:

```ini
WorkingDirectory=/opt/dota-lobby-streamer-proxy
EnvironmentFile=/opt/dota-lobby-streamer-proxy/.env
ExecStart=/opt/dota-lobby-streamer-proxy/.venv/bin/uvicorn app.main:app --host ${APP_HOST} --port ${APP_PORT}
```

Important nuance found during debugging:

```text
/opt/dota-lobby-streamer-proxy/.venv/bin/uvicorn
```

has shebang pointing to:

```text
/opt/dota-twitch-lobby-bot/streamer_proxy/.venv/bin/python3
```

So `dota2` and `steam` packages are installed under:

```text
/opt/dota-twitch-lobby-bot/streamer_proxy/.venv/lib/python3.13/site-packages
```

Use this Python for library introspection:

```bash
REAL_PY="/opt/dota-twitch-lobby-bot/streamer_proxy/.venv/bin/python3"
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

Real Steam login and Dota GC launch are implemented and verified.

Verified:

```text
POST /dota/connect -> 200 OK
/dota/status -> connected=true, gc_started=true, real_adapter_ready=true
last_login_result="1"
last_gc_result="launch: None; ready: None"
last_gc_error=null
```

This means:

- Steam/Dota Python dependencies are installed.
- `DOTA_MOCK_MODE=false` works for the connect path.
- `STEAM_USERNAME` and `STEAM_PASSWORD` are accepted from local `.env`.
- `STEAM_SHARED_SECRET` is optional.
- One-time Steam Guard code from the official Steam app can be passed in the `/dota/connect` request.
- `Dota2Client.launch()` succeeds.
- `Dota2Client.wait_event('ready')` succeeds.

Implemented streamer endpoints:

```text
/dota/status
/dota/connect
/dota/create-lobby
/dota/lobby
/dota/invite
```

## Current Dota blocker

Real invite API calls return success at the library-call level, but the target player does not receive an invite.

Observed invite attempts:

```text
DOTA_INVITE_ATTEMPT_OK invite_to_lobby steam_id64 76561198807245109 None
DOTA_INVITE_ATTEMPT_OK invite_to_lobby account_id32 846979381 None
DOTA_INVITE_ATTEMPT_OK invite_to_party steam_id64 76561198807245109 job_1
DOTA_INVITE_ATTEMPT_OK invite_to_party account_id32 846979381 job_2
```

Important conclusion from library source:

```python
def invite_to_lobby(self, steam_id):
    if self.lobby is None:
        return
```

So `invite_to_lobby` returning `None` is a false success when `self.lobby is None`.

Current `/dota/lobby` state:

```json
{"lobby_exists":false,"lobby_id":null,"lobby_name":"Real Dota lobby not detected yet","mode":"real_pending","connected":true,"members":[]}
```

Current `/dota/create-lobby` result after waiting for `lobby_new` and `lobby_changed`:

```text
DOTA_CREATE_LOBBY_OK {'create_result': 'None', 'events': [{'lobby_new': 'None'}, {'lobby_changed': 'None'}], 'lobby_detected': False, 'lobby_id': None, 'leader_id': None}
```

So `create_practice_lobby()` sends the GC message but no `CSODOTALobby` shared object arrives; `self._dota.lobby` stays `None`.

## Dota library findings

Library path:

```text
/opt/dota-twitch-lobby-bot/streamer_proxy/.venv/lib/python3.13/site-packages/dota2/features/lobby.py
```

Relevant event constants:

```python
EVENT_LOBBY_INVITE = 'lobby_invite'
EVENT_LOBBY_INVITE_REMOVED = 'lobby_invite_removed'
EVENT_LOBBY_NEW = 'lobby_new'
EVENT_LOBBY_CHANGED = 'lobby_changed'
EVENT_LOBBY_REMOVED = 'lobby_removed'
```

Relevant source findings:

```python
def create_practice_lobby(self, password="", options=None):
    return self.create_tournament_lobby(password=password, options=options)

def create_tournament_lobby(self, password="", tournament_game_id=None, tournament_id=0, options=None):
    options = {} if options is None else options
    options["pass_key"] = password
    command = {
        "lobby_details": options,
        "pass_key": password
    }
    self.send(EDOTAGCMsg.EMsgGCPracticeLobbyCreate, command)
```

`create_practice_lobby()` is fire-and-forget. Lobby appears only if SOCache receives `ESOType.CSODOTALobby` and emits `lobby_new` / `lobby_changed`.

## Most recent code changes already pushed

Recent streamer commits include:

```text
cb32ead Try Dota invite with multiple id variants
e4d70ae Add Dota practice lobby creation endpoint
308a9c6 Wait for Dota practice lobby creation event
4277c81 Wait for Dota GC ready before lobby creation
```

Backend commits include Steam Guard input and Dota status in Control Center:

```text
13f8b67 Pass Steam Guard code from backend client
05ab1fa Accept Steam Guard code in backend Dota connect route
ec54329 Add Steam Guard input and Dota status to dashboard
```

## Dota env shape

```env
DOTA_MOCK_MODE=false
DOTA_LOBBY_ID=
DOTA_LOBBY_NAME=
DOTA_ACCOUNT_ID=
STEAM_USERNAME=
STEAM_PASSWORD=
STEAM_SHARED_SECRET=
```

Real Steam/Dota credentials stay in local `.env` only and must not be committed.

`STEAM_SHARED_SECRET` is optional. For normal streamer onboarding, use a one-time Steam Guard code from the official Steam mobile app when calling `/dota/connect`.

## Commands for next chat

Check service and current status:

```bash
cd /opt/dota-lobby-streamer-proxy
KEY=$(grep '^PROXY_API_KEY=' .env | cut -d= -f2-)

curl -s -H "X-Api-Key: $KEY" http://127.0.0.1:8081/dota/status
echo
curl -i -H "X-Api-Key: $KEY" http://127.0.0.1:8081/dota/lobby
journalctl -u streamer-proxy -n 160 --no-pager
```

Connect after restart:

```bash
STEAM_GUARD_CODE="12345"
curl -i -X POST \
  -H "X-Api-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"steam_guard_code\":\"$STEAM_GUARD_CODE\"}" \
  http://127.0.0.1:8081/dota/connect
```

Try lobby creation:

```bash
curl -i -X POST \
  -H "X-Api-Key: $KEY" \
  http://127.0.0.1:8081/dota/create-lobby

curl -s -H "X-Api-Key: $KEY" http://127.0.0.1:8081/dota/status
echo
```

Try invite:

```bash
REAL_STEAM_ID="76561198807245109"
curl -i -X POST \
  -H "X-Api-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"steam_id\":\"$REAL_STEAM_ID\"}" \
  http://127.0.0.1:8081/dota/invite
```

## Next investigation step

The next assistant should continue from this exact blocker:

```text
Dota GC is ready, but create_practice_lobby does not produce lobby_new/lobby_changed and self._dota.lobby remains None.
```

Recommended next attempts:

1. Inspect Dota GC connection/state handling in `dota2/client.py` and `features/sharedobjects.py`.
2. Verify whether `client.games_played([570])` must be called before `Dota2Client.launch()`; a patch was proposed but not confirmed as applied/pushed at the time of this doc update.
3. Add `client.games_played([570])` immediately after Steam login and before `Dota2Client(client).launch()` if not already present.
4. Inspect whether `Dota2Client` needs `idle()`/gevent loop cooperation while waiting for SOCache updates.
5. Consider using `self._dota.send_job(...)` / `wait_msg(...)` for create lobby if a response message exists, but source currently uses fire-and-forget `send` for `EMsgGCPracticeLobbyCreate`.
6. Continue only after reading `docs/CURRENT_STATUS.md`, `docs/AI_NOTES.md`, `docs/project_context.md`, and `PROJECT_FILES.txt` from GitHub `main`.

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
