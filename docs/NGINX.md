# Nginx configuration

This repository includes an example nginx config for exposing the Twitch OAuth callback to the streamer proxy.

## Required public route

```text
https://test.raze1x6.mom/twitch/callback -> http://127.0.0.1:8081/twitch/callback
```

The example config is stored at:

```text
deploy/nginx/dota-lobby-streamer-proxy.conf
```

## Install on server

Run on the streamer server:

```bash
cd /opt/dota-lobby-streamer-proxy
git pull origin main

cp deploy/nginx/dota-lobby-streamer-proxy.conf /etc/nginx/sites-available/dota-lobby-streamer-proxy
ln -sf /etc/nginx/sites-available/dota-lobby-streamer-proxy /etc/nginx/sites-enabled/dota-lobby-streamer-proxy

nginx -t
systemctl reload nginx
```

## Test callback routing

```bash
curl -i "https://test.raze1x6.mom/twitch/callback?code=test"
journalctl -u streamer-proxy -n 80 --no-pager
```

Expected streamer-proxy log contains:

```text
GET /twitch/callback?code=test
```

A Twitch response like this is expected for the manual `code=test` probe:

```text
TWITCH_TOKEN_ERROR 400 {"status":400,"message":"Invalid authorization code"}
```

That error confirms nginx routing and FastAPI callback handling work. It does not indicate a real OAuth failure unless it happens with a fresh Twitch-generated authorization code.

## Current verified server state

As of 2026-05-05, the HTTPS public callback route reaches streamer proxy successfully:

```text
TWITCH_TOKEN_ERROR 400 {"status":400,"message":"Invalid authorization code"}
redirect_uri= https://test.raze1x6.mom/twitch/callback
89.127.214.228:0 - "GET /twitch/callback?code=test HTTP/1.1" 502 Bad Gateway
```

The `502` is produced by the app because `code=test` is intentionally invalid for Twitch token exchange.

## Certbot / HTTPS state

Certbot has been run for `test.raze1x6.mom`, and HTTPS callback testing has reached `streamer-proxy`.

The next step after HTTPS verification is to generate a fresh Twitch auth URL from `/twitch/auth-url`, authorize in the browser, and let Twitch redirect to the HTTPS callback with a real one-time `code`.

## HTTPS note

If the project uses HTTPS-only routing or Certbot-managed server blocks, merge the `location /twitch/` block into the existing HTTPS `server` block for `test.raze1x6.mom` instead of creating a competing server block.
