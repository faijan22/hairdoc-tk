#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
BRANCH="${HAIRDOC_BRANCH:-main}"

if [[ ! "${BRANCH}" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  echo "Invalid deployment branch." >&2
  exit 1
fi
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Copy .env.example to .env and add staging secrets." >&2
  exit 1
fi
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "Docker Engine with Compose v2 is required." >&2
  exit 1
fi

exec 9>"/tmp/hairdoc-tk-staging-deploy.lock"
if ! flock -n 9; then
  echo "Another staging deployment is already running." >&2
  exit 1
fi

cd "${REPO_ROOT}"
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "The server checkout has tracked changes. Refusing to overwrite them." >&2
  exit 1
fi

echo "==> Updating ${BRANCH}"
git fetch origin "${BRANCH}"
git checkout "${BRANCH}"
git pull --ff-only origin "${BRANCH}"

COMPOSE=(docker compose --env-file "${ENV_FILE}" -f "${SCRIPT_DIR}/compose.yml")

echo "==> Building the backend image"
"${COMPOSE[@]}" build --pull api

echo "==> Starting PostgreSQL and Redis"
"${COMPOSE[@]}" up -d postgres redis

echo "==> Validating the staging configuration"
"${COMPOSE[@]}" run --rm api python manage.py check --deploy

echo "==> Applying database migrations"
"${COMPOSE[@]}" run --rm api python manage.py migrate --noinput

echo "==> Collecting Django Admin static files"
"${COMPOSE[@]}" run --rm api python manage.py collectstatic --noinput --clear

echo "==> Starting API, realtime messaging, workers and scheduler"
"${COMPOSE[@]}" up -d --remove-orphans api worker beat

echo "==> Waiting for the API health check"
for attempt in $(seq 1 30); do
  if "${COMPOSE[@]}" exec -T api python -c \
    "import urllib.request; request=urllib.request.Request('http://127.0.0.1:8000/api/v1/health/', headers={'X-Forwarded-Proto':'https'}); urllib.request.urlopen(request, timeout=3).read()" \
    >/dev/null 2>&1; then
    break
  fi
  if [[ "${attempt}" == "30" ]]; then
    echo "API health check failed." >&2
    "${COMPOSE[@]}" logs --tail=120 api
    exit 1
  fi
  sleep 2
done

DOMAIN="$(sed -n 's/^HAIRDOC_DOMAIN=//p' "${ENV_FILE}" | tail -n 1 | tr -d '\r')"
if [[ -n "${DOMAIN}" ]]; then
  echo "==> Verifying public HTTPS"
  curl --fail --silent --show-error --retry 12 --retry-delay 5 --retry-connrefused \
    "https://${DOMAIN}/api/v1/health/" >/dev/null
fi

"${COMPOSE[@]}" ps
echo "Staging deployment completed successfully."

