# HairDoc TK staging deployment

This stack runs the Django ASGI API, WebSockets, PostgreSQL, Redis, Celery worker
and Celery beat. Daphne is published only on `127.0.0.1:18010`; the server's
existing aaPanel Apache installation owns public HTTPS. Database, Redis and
private media are never exposed directly.

## 1. Cloudflare

Create an `A` record:

- Name: `hairdoctk-dev`
- Target: the server's public IPv4 address
- Proxy: **DNS only** for the first deployment

Allow inbound SSH, TCP 80 and TCP 443 in the server/provider firewall. Do not
expose 5432, 6379, 8000 or 18010.

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
https://hairdoctk-dev.livecoder.tech/api/v1/integrations/stripe/webhook/
```

## 4. aaPanel Apache site

In aaPanel, add `hairdoctk-dev.livecoder.tech` as a website and issue its Let's
Encrypt certificate while Cloudflare is DNS-only. Configure it as a reverse
proxy to `http://127.0.0.1:18010`, preserve the original host, and enable
WebSockets. The equivalent Apache directives are in
`deploy/staging/apache-proxy.conf.example`; place them inside the site's HTTPS
virtual host if configuring Apache directly. Do not edit the global Apache
listener or replace aaPanel-managed certificates.

## 5. First deployment

```bash
cd /opt/hairdoc-tk
bash deploy/staging/deploy.sh
```

The deploy command performs a fast-forward Git pull, builds the image, starts
PostgreSQL/Redis, validates fail-closed staging settings, applies migrations,
collects and safely serves Admin static files, starts Daphne/Channels and Celery
worker/beat, then verifies internal and public health checks through Apache.

Expected health URL:

```text
https://hairdoctk-dev.livecoder.tech/api/v1/health/
```

Verify that Apache is actually upgrading the public WebSocket path:

```bash
curl -i --http1.1 --max-time 10 \
  -H 'Connection: Upgrade' \
  -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Version: 13' \
  -H 'Sec-WebSocket-Key: SGFpcmRvY1RLVGVzdEtleQ==' \
  'https://hairdoctk-dev.livecoder.tech/ws/v1/inbox/?ticket=invalid'
```

An invalid one-use ticket should be rejected by Daphne (HTTP 403), proving the
upgrade reached Channels. HTTP 404 means the `/ws/` `ProxyPass` lines are not
inside the active HTTPS virtual host or appear after its catch-all `/` proxy.

Create TK's first server account after deployment:

```bash
docker compose --env-file deploy/staging/.env -f deploy/staging/compose.yml \
  exec api python manage.py createsuperuser
```

## 6. One-command deployments from Windows

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

## 7. App connection

Run Expo against the hosted API instead of the LAN backend:

```powershell
cd apps/mobile
$env:EXPO_PUBLIC_API_URL="https://hairdoctk-dev.livecoder.tech/api/v1"
$env:EXPO_PUBLIC_REALTIME_API_URL="https://hairdoctk-dev.livecoder.tech/api/v1"
npx expo start --tunnel --go --clear
```

REST uses HTTPS and chat converts the configured origin to WSS. Local backend,
Metro proxy and same-Wi-Fi access are no longer involved.

## Operations

```bash
cd /opt/hairdoc-tk
docker compose --env-file deploy/staging/.env -f deploy/staging/compose.yml ps
docker compose --env-file deploy/staging/.env -f deploy/staging/compose.yml logs -f api worker beat
```

Named Docker volumes preserve PostgreSQL, Redis and staging media across
deployments. aaPanel manages TLS certificates. These are not backups. Encrypted
database/media backups and a tested restore procedure remain mandatory before
real patient data is used.

