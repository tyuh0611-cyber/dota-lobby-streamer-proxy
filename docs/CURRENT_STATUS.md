# Current status — streamer proxy

Last updated: 2026-05-05

## Repository

Repo:

```text
tyuh0611-cyber/dota-lobby-streamer-proxy

This repository owns streamer-side logic:

Twitch OAuth
Twitch access/refresh tokens
Twitch chatters endpoint
Dota lobby endpoint
Dota invite endpoint
future Steam/Dota Game Coordinator integration

Backend UI, database, queue ranking, and Control Center belong in:

tyuh0611-cyber/dota-lobby-backend
Current service path

Systemd should run from:

WorkingDirectory=/opt/dota-lobby-streamer-proxy
EnvironmentFile=/opt/dota-lobby-streamer-proxy/.env
ExecStart=/opt/dota-lobby-streamer-proxy/.venv/bin/uvicorn app.main:app --host ${APP_HOST} --port ${APP_PORT}

Confirmed current systemctl cat streamer-proxy already points to the new path.

Current active problem

Twitch OAuth callback reaches FastAPI successfully.

Confirmed by logs:

/opt/dota-lobby-streamer-proxy/app/main.py
twitch_callback -> twitch_client.exchange_code(code)

Current failure is inside Twitch token exchange:

https://id.twitch.tv/oauth2/token
HTTP 400 Bad Request

This means nginx and callback routing are no longer the primary problem.

Most likely causes:

Wrong or empty TWITCH_CLIENT_SECRET.
PUBLIC_BASE_URL / TWITCH_REDIRECT_URI mismatch.
Twitch Developer Console redirect URL mismatch.
Reused or expired Twitch code.
Auth URL was generated with a different redirect URI than token exchange uses.
Current fix added

app/twitch_client.py now logs Twitch token exchange errors as:

TWITCH_TOKEN_ERROR <status> <twitch_response> redirect_uri= <redirect_uri>

The callback now returns HTTP 502 with structured details instead of hiding the Twitch response behind an internal traceback.

Next test

Restart service:

systemctl restart streamer-proxy
sleep 2
systemctl status streamer-proxy --no-pager

Generate a new auth URL:

KEY=$(grep '^PROXY_API_KEY=' /opt/dota-lobby-streamer-proxy/.env | cut -d= -f2-)
curl -s -H "X-Api-Key: $KEY" http://127.0.0.1:8081/twitch/auth-url

Open the new URL in browser and authorize Twitch.

Then inspect logs:

journalctl -u streamer-proxy -n 120 --no-pager

Look for:

TWITCH_TOKEN_ERROR

The body will show the real Twitch reason.

Required env shape
PUBLIC_BASE_URL=https://test.raze1x6.mom
TWITCH_REDIRECT_URI=
TWITCH_CLIENT_ID=<from Twitch Developer Console>
TWITCH_CLIENT_SECRET=<from Twitch Developer Console>
TWITCH_ACCESS_TOKEN=
TWITCH_REFRESH_TOKEN=
TWITCH_BROADCASTER_ID=
TWITCH_MODERATOR_ID=

Twitch Developer Console must contain exactly:

https://test.raze1x6.mom/twitch/callback
AI workflow rule

Do not rely only on chat history.

Before work, read from GitHub main:

docs/CURRENT_STATUS.md
docs/AI_NOTES.md
docs/project_context.md
PROJECT_FILES.txt

After code changes, update docs and push to main.

## Twitch token exchange diagnostics added

A local diagnostic patch was added to `app/twitch_client.py`.

When Twitch token exchange fails, the service now logs:

```text
TWITCH_TOKEN_ERROR <status_code> <twitch_response> redirect_uri= <redirect_uri>

This is needed because Twitch currently returns:

HTTP 400 Bad Request
https://id.twitch.tv/oauth2/token

Callback routing is confirmed working because /twitch/callback reaches FastAPI and calls twitch_client.exchange_code(code).

The next step is to restart streamer-proxy, generate a new Twitch auth URL, authorize again, and read the exact TWITCH_TOKEN_ERROR line from journald.

Important: Twitch OAuth code is one-time use. Do not retry an old callback URL.
