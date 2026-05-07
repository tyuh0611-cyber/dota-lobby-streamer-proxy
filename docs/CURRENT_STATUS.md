# Current status — streamer proxy

Last updated: 2026-05-07

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

Important server nuance found during debugging:

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

Real Steam login and Dota GC launch are implemented and previously verified.

Verified before the current patch:

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

Real invite API calls returned success at the library-call level, but the target player did not receive an invite.

Important conclusion from library source:

```python
def invite_to_lobby(self, steam_id):
    if self.lobby is None:
        return
```

So `invite_to_lobby` returning `None` is a false success when `self.lobby is None`.

Last pre-patch `/dota/create-lobby` result:

```text
DOTA_CREATE_LOBBY_OK {'create_result': 'None', 'events': [{'lobby_new': 'None'}, {'lobby_changed': 'None'}], 'lobby_detected': False, 'lobby_id': None, 'leader_id': None}
```

So `create_practice_lobby()` sent the GC message but no `CSODOTALobby` shared object arrived; `self._dota.lobby` stayed `None`.

## Patch applied on 2026-05-07

Commit:

```text
4c73b102bb05bf420fb6e6989f95c09e0c231c9c Keep Dota GC operations on one gevent worker
```

What changed in `app/dota_real_adapter.py`:

- Verified `client.games_played([570])` was already present immediately after Steam login and before `Dota2Client(client)` / launch.
- Replaced ad-hoc `asyncio.to_thread(...)` calls with one persistent `ThreadPoolExecutor(max_workers=1, thread_name_prefix='dota-gevent')`.
- All Steam/Dota operations now run through `_run_sync(...)` on the same OS thread:
  - Steam login
  - `client.games_played([570])`
  - `Dota2Client(client)`
  - GC launch and `wait_event('ready')`
  - practice lobby create
  - invite calls
- Added `dota_worker: single_thread_gevent_executor` to `/dota/status` for deploy verification.
- Added `_idle_dota_sync(...)` using `gevent.sleep(...)` fallback to `time.sleep(...)` so Steam/Dota greenlets can process inbound GC/SOCache messages while waiting for lobby shared-object events.
- Extended lobby creation wait loop to poll `lobby_new` / `lobby_changed` in shorter chunks for up to ~35 seconds while idling gevent.

Reasoning:

The `steam`/`dota2` libraries use gevent internally. The old code created the Steam/Dota session in one arbitrary asyncio worker thread and then later called create-lobby/invite from another arbitrary worker thread. That can leave SOCache and event processing on the wrong gevent hub. The new code keeps the full Dota lifecycle on one persistent worker thread.

## Dota library findings

Library path on server:

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

## Commands for server after this patch

Deploy current `main` and restart:

```bash
cd /opt/dota-lobby-streamer-proxy
git pull --ff-only
systemctl restart streamer-proxy
sleep 2
journalctl -u streamer-proxy -n 80 --no-pager
```

Check service and confirm the new worker flag:

```bash
cd /opt/dota-lobby-streamer-proxy
KEY=$(grep '^PROXY_API_KEY=' .env | cut -d= -f2-)

curl -s -H "X-Api-Key: $KEY" http://127.0.0.1:8081/dota/status
echo
```

Expected after code deploy before reconnect:

```text
"dota_worker":"single_thread_gevent_executor"
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
curl -s -H "X-Api-Key: $KEY" http://127.0.0.1:8081/dota/lobby
echo
journalctl -u streamer-proxy -n 180 --no-pager
```

Only after `lobby_detected=true`, try invite:

```bash
REAL_STEAM_ID="76561198807245109"
curl -i -X POST \
  -H "X-Api-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"steam_id\":\"$REAL_STEAM_ID\"}" \
  http://127.0.0.1:8081/dota/invite
```

## Next investigation step if lobby is still not detected

Continue from this exact blocker:

```text
Dota GC is ready, single-thread gevent worker is active, but create_practice_lobby still does not produce lobby_new/lobby_changed and self._dota.lobby remains None.
```

Recommended next attempts:

1. On server, introspect installed `dota2/client.py`, `features/sharedobjects.py`, and `features/lobby.py` using `REAL_PY` above.
2. Confirm whether `Dota2Client` exposes lower-level SOCache state or callbacks for `CSODOTALobby`.
3. Inspect whether the create-lobby GC message needs different option fields for the installed Dota2 protocol version.
4. Consider adding a temporary diagnostic endpoint that prints GC/SOCache object type names after create-lobby.
5. Consider using `send_job(...)` / `wait_msg(...)` only if the installed protocol exposes a specific create-lobby response message; current library code uses fire-and-forget `send(...)` for `EMsgGCPracticeLobbyCreate`.

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
