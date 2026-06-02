#!/usr/bin/env bash
set -euo pipefail

BACKEND_SERVICE="owlsome-backend"
FRONTEND_SERVICE="owlsome-frontend"
DEFAULT_PUBLIC_HOST="owlsome.lilystudio.space"
BACKEND_PORT="${OWLSOME_BACKEND_PORT:-37800}"
FRONTEND_PORT="${OWLSOME_FRONTEND_PORT:-5173}"

log() {
  printf '\n[Owlsome] %s\n' "$1"
}

die() {
  printf '\n[Owlsome][ERROR] %s\n' "$1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

if [[ "$(uname -s)" != "Linux" ]]; then
  die "This installer only supports Linux servers."
fi

if [[ "${EUID}" -ne 0 ]]; then
  die "Please run with root privileges: sudo bash deployment/systemd/install_owlsome_services.sh"
fi

if ! command -v systemctl >/dev/null 2>&1 || [[ ! -d /run/systemd/system ]]; then
  die "systemd is not available. This script must run on a systemd-based Linux server."
fi

require_command python3
require_command npm
require_command curl

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DETECTED_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ -n "${OWLSOME_ROOT:-}" ]]; then
  REPO_ROOT="$(cd "${OWLSOME_ROOT}" && pwd)"
elif [[ -d "${PWD}/learning_platform/backend" && -d "${PWD}/learning_platform/frontend" ]]; then
  REPO_ROOT="$(pwd)"
else
  REPO_ROOT="${DETECTED_ROOT}"
fi

BACKEND_DIR="${REPO_ROOT}/learning_platform/backend"
FRONTEND_DIR="${REPO_ROOT}/learning_platform/frontend"

[[ -d "${BACKEND_DIR}" ]] || die "Backend directory not found: ${BACKEND_DIR}"
[[ -d "${FRONTEND_DIR}" ]] || die "Frontend directory not found: ${FRONTEND_DIR}"

log "Using repository root: ${REPO_ROOT}"
log "Using backend port: ${BACKEND_PORT}"
log "Using frontend port: ${FRONTEND_PORT}"

generate_token() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 24
  elif [[ -r /proc/sys/kernel/random/uuid ]]; then
    tr -d '-' </proc/sys/kernel/random/uuid
  else
    date +%s%N
  fi
}

replace_or_append_env() {
  local file="$1"
  local key="$2"
  local value="$3"
  if grep -q "^${key}=" "${file}"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "${file}"
  else
    printf '\n%s=%s\n' "${key}" "${value}" >>"${file}"
  fi
}

log "Preparing backend environment"
cd "${BACKEND_DIR}"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

BACKEND_PYTHON="${BACKEND_DIR}/.venv/bin/python"
[[ -x "${BACKEND_PYTHON}" ]] || die "Python venv executable not found: ${BACKEND_PYTHON}"

"${BACKEND_PYTHON}" -m pip install --upgrade pip
"${BACKEND_PYTHON}" -m pip install -r requirements.txt

if [[ ! -f ".env" ]]; then
  cp .env.server.example .env
  ADMIN_TOKEN="$(generate_token)"
  replace_or_append_env ".env" "ADMIN_TOKEN" "${ADMIN_TOKEN}"
  log "Created backend .env and generated ADMIN_TOKEN: ${ADMIN_TOKEN}"
else
  log "Backend .env already exists; keeping current ADMIN_TOKEN and API settings."
fi

log "Preparing frontend environment"
cd "${FRONTEND_DIR}"

if [[ ! -f ".env.production" ]]; then
  cp .env.server.example .env.production
  replace_or_append_env ".env.production" "VITE_API_BASE_URL" "https://${DEFAULT_PUBLIC_HOST}"
  replace_or_append_env ".env.production" "VITE_PREVIEW_ALLOWED_HOSTS" "${DEFAULT_PUBLIC_HOST}"
  log "Created frontend .env.production for https://${DEFAULT_PUBLIC_HOST}"
fi

npm install
npm run build

NPM_BIN="$(command -v npm)"
NPM_DIR="$(dirname "${NPM_BIN}")"

log "Writing systemd service files"
cat >/etc/systemd/system/${BACKEND_SERVICE}.service <<EOF
[Unit]
Description=Owlsome Learning Backend
After=network.target

[Service]
Type=simple
WorkingDirectory=${BACKEND_DIR}
EnvironmentFile=${BACKEND_DIR}/.env
ExecStart=${BACKEND_PYTHON} -m uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/${FRONTEND_SERVICE}.service <<EOF
[Unit]
Description=Owlsome Learning Frontend Preview
After=network.target

[Service]
Type=simple
WorkingDirectory=${FRONTEND_DIR}
Environment=PATH=${NPM_DIR}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=${NPM_BIN} run preview -- --host 0.0.0.0 --port ${FRONTEND_PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

log "Enabling and restarting services"
systemctl daemon-reload
systemctl enable "${BACKEND_SERVICE}"
systemctl enable "${FRONTEND_SERVICE}"
systemctl restart "${BACKEND_SERVICE}"
systemctl restart "${FRONTEND_SERVICE}"

log "Verifying local services"
sleep 3
curl --fail --silent --show-error "http://127.0.0.1:${BACKEND_PORT}/api/health"
printf '\n'
curl --fail --silent --show-error --output /dev/null --write-out "Frontend HTTP status: %{http_code}\n" "http://127.0.0.1:${FRONTEND_PORT}"

log "Done. Useful commands:"
cat <<EOF
  systemctl status ${BACKEND_SERVICE} ${FRONTEND_SERVICE}
  journalctl -u ${BACKEND_SERVICE} -f
  journalctl -u ${FRONTEND_SERVICE} -f
  systemctl restart ${BACKEND_SERVICE} ${FRONTEND_SERVICE}

If this server is behind Nginx Proxy Manager, keep forwarding:
  https://${DEFAULT_PUBLIC_HOST}/      -> 127.0.0.1:${FRONTEND_PORT}
  https://${DEFAULT_PUBLIC_HOST}/api/  -> 127.0.0.1:${BACKEND_PORT}/api/
EOF
