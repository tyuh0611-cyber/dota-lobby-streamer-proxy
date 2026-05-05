#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/dota-lobby-streamer-proxy}"
SERVICE_NAME="${SERVICE_NAME:-streamer-proxy}"
APP_USER="${APP_USER:-dota-streamer-proxy}"
APP_GROUP="${APP_GROUP:-dota-streamer-proxy}"
ENV_FILE="$APP_DIR/.env"
NGINX_SITE="/etc/nginx/sites-available/dota-lobby-streamer-proxy"
NGINX_ENABLED="/etc/nginx/sites-enabled/dota-lobby-streamer-proxy"

need_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "Run as root."
    exit 1
  fi
}

ask() {
  local prompt="$1"
  local default_value="${2:-}"
  local value

  if [[ -n "$default_value" ]]; then
    read -r -p "$prompt [$default_value]: " value
    echo "${value:-$default_value}"
  else
    read -r -p "$prompt: " value
    echo "$value"
  fi
}

ask_secret() {
  local prompt="$1"
  local value
  read -r -s -p "$prompt: " value
  echo >&2
  echo "$value"
}

require_value() {
  local name="$1"
  local value="$2"

  if [[ -z "$value" ]]; then
    echo "$name is required."
    exit 1
  fi
}

generate_secret() {
  python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
}

write_env() {
  local key="$1"
  local value="$2"

  python3 - "$ENV_FILE" "$key" "$value" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]

lines = []
found = False

if path.exists():
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(key + "="):
            lines.append(f"{key}={value}")
            found = True
        else:
            lines.append(line)

if not found:
    lines.append(f"{key}={value}")

path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
path.chmod(0o600)
PY
}

read_env() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | head -n1 | cut -d= -f2- || true
}

install_packages() {
  apt update
  DEBIAN_FRONTEND=noninteractive apt install -y \
    python3 python3-venv python3-pip git curl nginx certbot python3-certbot-nginx ca-certificates
}

ensure_user() {
  if ! getent group "$APP_GROUP" >/dev/null; then
    groupadd --system "$APP_GROUP"
  fi

  if ! id "$APP_USER" >/dev/null 2>&1; then
    useradd --system --gid "$APP_GROUP" --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
  fi
}

setup_python() {
  cd "$APP_DIR"
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
}

write_systemd() {
  cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Dota Lobby Streamer Proxy
After=network.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${APP_DIR}/.venv/bin/uvicorn app.main:app --host \${APP_HOST} --port \${APP_PORT}
Restart=always
RestartSec=5
User=${APP_USER}
Group=${APP_GROUP}
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=${APP_DIR}

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable "$SERVICE_NAME"
}

write_nginx_http_site() {
  local domain="$1"

  if [[ -f "$NGINX_SITE" ]]; then
    cp "$NGINX_SITE" "${NGINX_SITE}.bak.$(date +%Y%m%d%H%M%S)"
  fi

  cat > "$NGINX_SITE" <<EOF
server {
    listen 80;
    server_name ${domain};

    location /twitch/ {
        proxy_pass http://127.0.0.1:8081;
        proxy_http_version 1.1;

        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

  ln -sf "$NGINX_SITE" "$NGINX_ENABLED"
  nginx -t
  systemctl reload nginx
}

run_certbot() {
  local domain="$1"
  local email="$2"

  certbot --nginx \
    --non-interactive \
    --agree-tos \
    --redirect \
    --email "$email" \
    -d "$domain"

  nginx -t
  systemctl reload nginx
}

write_base_env() {
  local domain="$1"
  local twitch_client_id="$2"
  local twitch_client_secret="$3"
  local proxy_api_key="$4"
  local dota_mock_mode="$5"
  local steam_username="$6"
  local steam_password="$7"
  local steam_shared_secret="$8"

  touch "$ENV_FILE"
  chmod 600 "$ENV_FILE"

  write_env APP_HOST "0.0.0.0"
  write_env APP_PORT "8081"
  write_env PUBLIC_BASE_URL "https://${domain}"
  write_env TWITCH_REDIRECT_URI ""
  write_env PROXY_API_KEY "$proxy_api_key"
  write_env ALLOWED_CLIENT_IP ""

  write_env TWITCH_CLIENT_ID "$twitch_client_id"
  write_env TWITCH_CLIENT_SECRET "$twitch_client_secret"
  write_env TWITCH_ACCESS_TOKEN "$(read_env TWITCH_ACCESS_TOKEN)"
  write_env TWITCH_REFRESH_TOKEN "$(read_env TWITCH_REFRESH_TOKEN)"
  write_env TWITCH_BROADCASTER_ID "$(read_env TWITCH_BROADCASTER_ID)"
  write_env TWITCH_MODERATOR_ID "$(read_env TWITCH_MODERATOR_ID)"
  write_env TWITCH_SCOPES "moderator:read:chatters"

  write_env DOTA_MOCK_MODE "$dota_mock_mode"
  write_env STEAM_USERNAME "$steam_username"
  write_env STEAM_PASSWORD "$steam_password"
  write_env STEAM_SHARED_SECRET "$steam_shared_secret"
}

start_service() {
  systemctl restart "$SERVICE_NAME"
  sleep 2
  systemctl status "$SERVICE_NAME" --no-pager || true
}

print_auth_url() {
  local key auth_json auth_url

  key="$(read_env PROXY_API_KEY)"
  auth_json="$(curl -fsS -H "X-Api-Key: ${key}" "http://127.0.0.1:8081/twitch/auth-url")"
  auth_url="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["url"])' "$auth_json")"

  echo
  echo "Open this Twitch authorization URL in the streamer's browser:"
  echo
  echo "$auth_url"
  echo
}

wait_for_oauth_tokens() {
  print_auth_url

  echo "After Twitch redirects to /twitch/callback, return here."
  read -r -p "Press Enter after Twitch authorization is complete... " _

  local access refresh
  access="$(read_env TWITCH_ACCESS_TOKEN)"
  refresh="$(read_env TWITCH_REFRESH_TOKEN)"

  if [[ -z "$access" || -z "$refresh" ]]; then
    echo "Twitch tokens are still empty. Recent logs:"
    journalctl -u "$SERVICE_NAME" -n 120 --no-pager || true
    exit 1
  fi
}

fill_twitch_user_ids() {
  local client_id access_token response twitch_user_id

  client_id="$(read_env TWITCH_CLIENT_ID)"
  access_token="$(read_env TWITCH_ACCESS_TOKEN)"

  response="$(curl -fsS \
    -H "Client-Id: ${client_id}" \
    -H "Authorization: Bearer ${access_token}" \
    "https://api.twitch.tv/helix/users")"

  twitch_user_id="$(python3 -c 'import json,sys; p=json.loads(sys.argv[1]); d=p.get("data") or []; print(d[0].get("id","") if d else "")' "$response")"

  require_value TWITCH_USER_ID "$twitch_user_id"

  write_env TWITCH_BROADCASTER_ID "$twitch_user_id"
  write_env TWITCH_MODERATOR_ID "$twitch_user_id"

  echo "Saved TWITCH_BROADCASTER_ID and TWITCH_MODERATOR_ID: $twitch_user_id"
}

test_callback() {
  local domain="$1"

  echo
  echo "Testing HTTPS callback route..."
  curl -i "https://${domain}/twitch/callback?code=test" || true
  echo
  echo "Expected app-side result for code=test is Invalid authorization code."
}

test_chatters() {
  local key
  key="$(read_env PROXY_API_KEY)"

  echo
  echo "Testing /chatters..."
  curl -i -H "X-Api-Key: ${key}" "http://127.0.0.1:8081/chatters"
}

main() {
  need_root

  echo "Dota Lobby Streamer Proxy installer"
  echo

  local domain email twitch_client_id twitch_client_secret proxy_api_key
  local dota_mock_mode steam_username steam_password steam_shared_secret

  domain="$(ask 'Domain for streamer proxy, without https' 'test.raze1x6.mom')"
  email="$(ask 'Email for Certbot / Let’s Encrypt')"
  twitch_client_id="$(ask 'Twitch Client ID')"
  twitch_client_secret="$(ask_secret 'Twitch Client Secret')"

  proxy_api_key="$(ask 'Proxy API key, leave empty to generate' '')"
  if [[ -z "$proxy_api_key" ]]; then
    proxy_api_key="$(generate_secret)"
    echo "Generated PROXY_API_KEY. Save it for backend integration."
  fi

  dota_mock_mode="$(ask 'Use Dota mock mode? true/false' 'true')"
  steam_username=""
  steam_password=""
  steam_shared_secret=""

  if [[ "$dota_mock_mode" == "false" ]]; then
    steam_username="$(ask 'Steam username')"
    steam_password="$(ask_secret 'Steam password')"
    steam_shared_secret="$(ask_secret 'Steam shared secret')"
  fi

  require_value DOMAIN "$domain"
  require_value EMAIL "$email"
  require_value TWITCH_CLIENT_ID "$twitch_client_id"
  require_value TWITCH_CLIENT_SECRET "$twitch_client_secret"

  install_packages
  ensure_user
  setup_python
  write_base_env "$domain" "$twitch_client_id" "$twitch_client_secret" "$proxy_api_key" "$dota_mock_mode" "$steam_username" "$steam_password" "$steam_shared_secret"

  chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"

  write_systemd
  start_service

  write_nginx_http_site "$domain"
  run_certbot "$domain" "$email"
  test_callback "$domain"

  echo
  echo "Important: Twitch Developer Console redirect URL must be exactly:"
  echo "https://${domain}/twitch/callback"
  echo

  wait_for_oauth_tokens
  fill_twitch_user_ids

  start_service
  test_chatters

  echo
  echo "Installer finished."
  echo
  echo "Local .env contains streamer secrets and must not be committed."
  echo "Backend must use this PROXY_API_KEY:"
  echo "$proxy_api_key"
}

main "$@"
