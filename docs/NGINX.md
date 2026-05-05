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
curl -i "http://test.raze1x6.mom/twitch/callback?code=test"
journalctl -u streamer-proxy -n 50 --no-pager
```

Expected streamer-proxy log contains:

```text
GET /twitch/callback?code=test
```

If the project uses HTTPS-only routing or Certbot-managed server blocks, merge the `location /twitch/` block into the existing HTTPS `server` block for `test.raze1x6.mom` instead of creating a competing server block.
