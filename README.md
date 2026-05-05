# Dota Lobby Streamer Proxy

Streamer-side proxy for the Dota Twitch Lobby project.

## Purpose

This service runs on the streamer server and owns streamer-sensitive integrations.

It manages:

- Twitch OAuth
- Twitch chatters access
- Twitch access/refresh token storage
- Steam credentials
- future real Dota Game Coordinator integration
- limited HTTP API for the backend

## Runtime role

```text
backend server -> streamer proxy -> Twitch / Steam / Dota
```

The backend calls this service through a small HTTP API protected by `X-Api-Key`.

## Security boundary

Streamer proxy may store real streamer secrets in local `.env` only.

Never commit:

- `.env`
- Twitch access token
- Twitch refresh token
- Steam password
- Steam shared secret

## Setup strategy

Streamer should not manually edit many files.

Installation should ask for:

```text
PUBLIC_BASE_URL
PROXY_API_KEY or generate one
TWITCH_CLIENT_ID
TWITCH_CLIENT_SECRET
DOTA_MOCK_MODE
```

Later, when real Dota integration is enabled:

```text
STEAM_USERNAME
STEAM_PASSWORD
STEAM_SHARED_SECRET
```

OAuth should fill automatically:

```text
TWITCH_ACCESS_TOKEN
TWITCH_REFRESH_TOKEN
TWITCH_BROADCASTER_ID
TWITCH_MODERATOR_ID
```

## Important current fix

Twitch OAuth redirect must use public URL, not localhost.

Required local env value:

```env
PUBLIC_BASE_URL=https://test.raze1x6.mom
```

The generated Twitch redirect URL must be exactly:

```text
https://test.raze1x6.mom/twitch/callback
```

and must match the Twitch Developer Console app redirect URL exactly.

## Notes for ChatGPT / future AI work

Keep project notes updated in:

```text
docs/AI_NOTES.md
docs/project_context.md
PROJECT_FILES.txt
```

Whenever structure changes, update `PROJECT_FILES.txt`.
Whenever streamer setup/OAuth/Dota strategy changes, update `docs/project_context.md` and `docs/AI_NOTES.md`.
