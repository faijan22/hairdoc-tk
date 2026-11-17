# HairDoc TK staging deployment

This stack runs the Django ASGI API, WebSockets, PostgreSQL, Redis, Celery worker,
Celery beat and Caddy HTTPS proxy. Only ports 80/443 are published. Database,
Redis and private media are never exposed directly.

## 1. Cloudflare

Create an `A` record:

- Name: `api-dev.hairdoctk`
- Target: the server's public IPv4 address
- Proxy: **DNS only** for the first deployment

Allow inbound SSH, TCP 80, TCP 443 and UDP 443 in the server/provider firewall.
Do not expose 5432, 6379 or 8000.

After the first deployment returns a valid HTTPS health response, Cloudflare may
be switched to proxied mode. Set SSL/TLS to **Full (strict)** and leave WebSockets
enabled. Never use Flexible SSL.

## 2. One-time Ubuntu server setup

```bash
sudo apt-get update && sudo apt-get install -y git
sudo mkdir -p /opt/hairdoc-tk
sudo chown "$USER":"$USER" /opt/hairdoc-tk
git clone https://github.com/faijan22/hairdoc-tk.git /opt/hairdoc-tk
cd /opt/hairdoc-tk
sudo bash deploy/staging/bootstrap-ubuntu.sh
```

Log out and back in once after Docker group membership changes, then verify:

```bash
docker version
docker compose version
```

For a private GitHub repository, configure a read-only deploy key on the server
before cloning/pulling.

## 3. Staging secrets

```bash
cd /opt/hairdoc-tk/deploy/staging
cp .env.example .env
openssl rand -base64 48   # use for DJANGO_SECRET_KEY
openssl rand -hex 32      # safe POSTGRES_PASSWORD value
nano .env
```

Replace every `replace...` value. Use only Stripe **test** credentials and the
test destination's real `whsec_...` signing secret. The `.env` file is ignored
by Git and must never be committed or posted in chat.

The Stripe staging destination is:

```text
https://api-dev.hairdoctk.livecoder.tech/api/v1/integrations/stripe/webhook/
```

## 4. First deployment

```bash
cd /opt/hairdoc-tk
bash deploy/staging/deploy.sh
```

The deploy command performs a fast-forward Git pull, builds the image, starts
PostgreSQL/Redis, validates fail-closed staging settings, applies migrations,
collects Admin static files, starts Daphne/Channels, Celery worker/beat and Caddy,
then verifies internal and public health checks.

Expected health URL:

```text
https://api-dev.hairdoctk.livecoder.tech/api/v1/health/
```

Create TK's first server account after deployment:

```bash
docker compose --env-file deploy/staging/.env -f deploy/staging/compose.yml \
  exec api python manage.py createsuperuser
```

## 5. One-command deployments from Windows

Set these once in the PowerShell session (or as Windows user environment
variables):

```powershell
$env:HAIRDOC_DEPLOY_TARGET="deploy@YOUR_SERVER_IP"
$env:HAIRDOC_DEPLOY_PATH="/opt/hairdoc-tk"
$env:HAIRDOC_DEPLOY_BRANCH="main"
```

After code is committed, deploy with:

```powershell
npm run deploy:staging
```

It refuses a dirty local tree, pushes the committed branch, connects over SSH,
pulls with `--ff-only`, runs migrations and restarts the complete stack. It never
copies `.env` or secrets from the developer machine.

## 6. App connection

Run Expo against the hosted API instead of the LAN backend:

```powershell
cd apps/mobile
$env:EXPO_PUBLIC_API_URL="https://api-dev.hairdoctk.livecoder.tech/api/v1"
$env:EXPO_PUBLIC_REALTIME_API_URL="https://api-dev.hairdoctk.livecoder.tech/api/v1"
npx expo start --tunnel --go --clear
```

REST uses HTTPS and chat converts the configured origin to WSS. Local backend,
Metro proxy and same-Wi-Fi access are no longer involved.

## Operations

```bash
cd /opt/hairdoc-tk
docker compose --env-file deploy/staging/.env -f deploy/staging/compose.yml ps
docker compose --env-file deploy/staging/.env -f deploy/staging/compose.yml logs -f api worker beat proxy
```

Named Docker volumes preserve PostgreSQL, Redis, TLS state and staging media
across deployments. They are not a backup. Encrypted database/media backups and
a tested restore procedure remain mandatory before real patient data is used.

