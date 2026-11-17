# HairDoc TK

HairDoc TK is an Expo mobile app with a Django API for photo-first private hair/scalp consultations, booking, Stripe payments, client↔TK messaging, versioned coaching plans, progress check-ins, and persisted care notifications. Clients upload intake and follow-up photos; TK may arrange an external live call in Messages only when needed. Release hardening remains unbuilt; Phase 2 remains planned only.

## Current state

- Expo SDK 57.0.21 + React Native 0.86.3 + React 19.2 + TypeScript 6 + Expo Router, aligned with the SDK 57 client used for physical-iPhone testing.
- Intentional light-only Phase 1 theme, accessible UI primitives, reduced-motion support, and a reference-led three-step onboarding flow.
- The owner-approved system uses modern native typography, 20px mobile gutters, strong whitespace, layered soft cards, and a restrained sage/deep-forest palette; red is danger-only. Web requests SF Pro Display/Text with native system fallbacks. Opaque theme-matched route fades avoid transition flashes and respect reduced-motion preferences.
- Signed-out Explore is a responsive editorial landing with account/sign-in actions only. Consultation services, prices, service details, intake, and authenticated Home data require login at both UI and API boundaries.
- `GET /api/v1/home/` composes published content publicly and adds services plus the current consultation/next appointment only for an authenticated client; Explore is the canonical post-sign-in destination and never fabricates demo data.
- A public HairDoc hub reads published entries from `GET /api/v1/content/`; content is managed in Django Admin.
- Email registration/verification, sign-in, forgot/reset/change password, protected account routing, and device session management.
- Grouped Settings UI with editable personal/hair profiles, IANA timezone, notification preferences, security controls, and versioned legal/consent records.
- Admin-managed consultation services and immutable questionnaire versions, with authenticated resumable intake, locked snapshots, and consent-gated private photos.
- Patient camera/library flow requests the relevant native permission at the moment of use, then performs safe JPEG normalization, upload/retry/delete feedback, short-lived signed reads, access audit, and read-only final submission.
- Expert-assignment-gated TK workspace shows the latest submitted photo review and provides client context, intake answers, hair-profile snapshots, photo sets, appointments, messages, availability, and scoped payment activity; Django Admin is configuration/developer fallback.
- TK-managed recurring hours and date exceptions, server-generated DST-safe slots, patient booking review, 30-minute payment-pending holds, reschedule/cancel, and staff/client appointment views.
- Server-priced booking: no-charge consultations confirm without creating a payment; paid consultations use Stripe-hosted Checkout behind a payment adapter, signature-verified/replay-safe webhooks, payment history, and in-app receipts. Card data never enters HairDoc TK.
- Consultation-linked one-client/TK messaging with durable PostgreSQL history, optimistic text/private-image sends, typing presence, one-tick `Sent`/two-tick `Read`, idempotent REST writes, foreground-aware alerts, and live Django Channels delivery. Redis is realtime fan-out, not message storage.
- Photo-first consultations with optional externally arranged calls. `VideoProvider` defaults to disabled; the dormant managed-video adapter cannot create rooms or costs unless explicitly re-enabled later.
- Consultation-bound coaching plans: the assigned TK account drafts structured guidance/recommendations in the app, publishing locks that version, and only the owning client can read it.
- Care-plan-gated progress check-ins: clients save structured updates and private follow-up photos; assigned TK compares them with baseline photos and explicitly publishes locked feedback.
- Mobile forms use a shared keyboard-aware scroll foundation: iOS adjusts keyboard insets, Android uses resize/height avoidance, and fixed chat/modal inputs have dedicated handling.
- Role-specific home/navigation: clients see care actions; TK sees a clearly labelled expert workspace. A rounded floating bottom bar exposes only the five highest-frequency destinations.
- Owner-approved legal copy can include an Admin-uploaded PDF, TXT, MD, or DOCX file (10 MB maximum); the app displays body copy and opens the current published file through the versioned API.
- Account deletion is available in Settings and at `/account-deletion`: consequence review, password reauthentication, typed `DELETE`, explicit acknowledgement, session revocation, removal of private/profile/auth data, and de-identification of records retained for legitimate audit obligations.
- Short-lived in-memory access JWTs plus rotating opaque refresh tokens: hashed server-side, SecureStore on native, HTTP-only scoped SameSite cookie on web, and session-family revocation on reuse. Browser JavaScript never receives the web refresh secret.
- Django 5.2 LTS + DRF, PostgreSQL, ASGI/Channels/Celery configuration, versioned API routing, request IDs, structured API errors, and Django Admin.
- Google/Apple sign-in awaits owner-supplied provider identifiers/credentials; it has no placeholder UI or endpoint.

## Requirements

- Node.js 22.13+ or 24.3+ (Node 24 is currently verified)
- npm 11+
- Python 3.12+
- An Expo Go/client build compatible with SDK 57 on the physical phone
- Internet access for Expo tunnel mode; the same Wi-Fi/LAN is needed only for the direct-LAN fallback
- Docker only when using the included PostgreSQL/Redis services

## Quick start: physical device + local backend

From the repository root:

```powershell
npm run setup
npm run dev
```

`npm run dev`:

1. Detects the PC's active LAN IPv4 address and applies pending Django migrations.
2. Starts Django on `0.0.0.0:8000`.
3. Adds a development-only Metro bridge from the Expo tunnel to Django's `/api/v1` routes.
4. Starts the notification worker and appointment-reminder scheduler.
5. Starts Expo Go through its tunnel so both the bundle and local API are reachable on a physical device, retrying transient ngrok startup failures up to three times.
6. Stops Django, the worker, and the scheduler when Expo exits.

Scan the tunnel QR code printed by Expo Go. Complete or skip onboarding; the HairDoc hub should load its consultation entry point. With no published Admin content it shows the intentional empty state.

When deliberately running the two servers in separate terminals, tunnel mode automatically sends native API calls back through Metro to local Django:

```powershell
# apps/backend
python manage.py runserver 0.0.0.0:8000

# apps/mobile
npx expo start --tunnel --go --clear
```

The bridge exposes only `/api/v1` while that Metro session is running; Django authentication and object permissions still apply. Stop Expo after testing. Production settings and builds do not use this bridge and retain strict configured API hosts.

The project now targets SDK 57. Expo requires the project SDK and the installed Expo client runtime to match; run `npx expo-doctor@latest` after future upgrades. For production development, move from Expo Go to a project-owned development build so native runtime updates are controlled rather than dictated by the store client.

In local DEBUG mode, registration and recovery screens receive and prefill the one-time token so the complete flow is testable without an email vendor. Production never returns these tokens; it sends them through the configured email backend.

Terms, privacy, consultation-disclaimer, and photo/data-consent copy is never fabricated in the app. Create and publish owner-approved versions in Django Admin under **Legal documents**; legal-document screens intentionally show a preparing state until a version is published.

For each legal document, choose its type and version, add a title, then paste body copy, upload an approved PDF/TXT/MD/DOCX file, or do both. Set status to **Published**; the publication time is filled automatically when omitted. The file appears in **Settings → Privacy & legal**. Development files are stored under ignored `apps/backend/.media/`; production must use durable Django-compatible object storage.

Consultation pricing, duration, copy, and questions are also never hard-coded in the app. Edit them in Django Admin under **Consultation services**, then publish a valid **Questionnaire** with questions/options. New consultation cases snapshot those terms so later Admin edits do not rewrite patient history.

Local development deliberately allows the real camera/gallery upload flow before TK supplies approved Photo & Data Consent copy. It creates no fake consent or acceptance record; the nullable audit fields make that explicit. Base settings require consent by default, and production forces it on. Once approved copy is published, production patients must accept that exact current version before uploading or TK can view the photo.

Development photos are normalized to private JPEGs under `apps/backend/.private-media/`; only metadata is stored in PostgreSQL. That folder has no public Django media route and is git-ignored. Authenticated APIs issue five-minute signed reads to the patient or staff, and every successful read is audited. Back it up with the database when local data matters. Production must replace the configured `StorageProvider` with private object storage; do not deploy local disk as durable production storage.

For TK access, edit the intended account email and mark it `is_staff` and email-verified in Django Admin, then sign in again. **Open consultation workspace** appears in the HairDoc Hub and Settings. It lists only consultations whose patient submitted at least one consented photo; Django Admin remains available for catalogue/legal setup and developer troubleshooting.

Before patients can book, TK must open **Manage availability** in the app and save at least one weekly interval or extra-hours exception. The same database-backed rules are editable in Django Admin. Assign TK as the consultation service's expert in Django Admin when more than one staff account exists; with exactly one active staff account the backend safely uses that account. Client times are displayed in the device timezone, while rules remain in TK's chosen IANA timezone.

For a no-charge service, booking atomically confirms the appointment and creates its private client↔TK conversation without contacting Stripe. For a paid service, booking creates an approximately 30-minute `PAYMENT_PENDING` hold and opens Stripe-hosted Checkout. The app never treats the return page as proof of payment: only a signature-verified Stripe webhook can mark payment successful and atomically confirm the appointment. Expired unpaid holds are released.

### Stripe test-mode setup

Create or use TK's Stripe account. Copy only **test-mode** server credentials into ignored `apps/backend/.env`—never paste them into source control or chat:

```dotenv
STRIPE_ENVIRONMENT=test
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
PAYMENT_RETURN_BASE_URL=https://<public-api>/api/v1/payments/return
```

For local testing, use Stripe CLI to forward `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, `checkout.session.expired`, `refund.created`, `refund.updated`, and `refund.failed` to `http://127.0.0.1:8000/api/v1/integrations/stripe/webhook/`; copy the CLI's temporary `whsec_...` secret into `.env`, then restart Django. For a shared development API, configure the same events on its stable HTTPS Stripe webhook endpoint. The Expo Metro bridge is not a public webhook host.

Use Stripe's documented test cards only; no real charge occurs in test mode. Returning from Safari to Expo Go may be manual locally; the app refreshes payment state when active. Production requires `STRIPE_ENVIRONMENT=production`, a live `sk_live_`/`rk_live_` key, the production endpoint's own `whsec_` secret, HTTPS API/return URLs, and a separately tested live-mode webhook. Never reuse test webhook secrets in live mode.

### Video decision

No video account or paid video service is required. The default `DisabledVideoProvider` prevents in-app room creation. The care flow is intake + private photos + secure Messages; when a live conversation is useful, TK can arrange her chosen external platform in Messages. A dormant Daily adapter remains behind the interface only to preserve a future migration path. Do not configure it, add billing, expose a video CTA, or promise health-data compliance without new owner approval and a privacy/cost review.

If the phone cannot connect:

- Let `npm run dev` finish its three tunnel attempts; a one-off `remote gone away` is normally transient and does not require reinstalling Expo.
- Restart Expo with `--clear` after any app/Metro configuration change.
- Disable the phone or PC VPN temporarily if it interferes with the Expo tunnel.
- If all attempts fail while ngrok reports healthy, allow Node.js/ngrok through antivirus or firewall, or try another internet connection/hotspot.
- Allow Python and Node.js through Windows Firewall on **Private networks** if Windows prompts.
- For direct-LAN diagnosis, open `http://<LAN-IP>:8000/api/v1/health/` in the phone browser.
- If the QR scanner fails, enter the tunnel URL printed by Expo in Expo Go.
- Local Network permission and guest-Wi-Fi client isolation affect only the direct-LAN fallback, not the tunnel API bridge.

If web or Expo Go shows **Unmatched Route** or the old **Hello World** page, stop the old Metro process with `Ctrl+C`, then run `npm run dev` again. Do not create routes under `apps/mobile/src/app`; Expo routes live only in `apps/mobile/app`.

The launcher requires ports `8000` (Django) and `8081` (Expo). It now fails before startup with a clear port message when an older local server is still running; stop that server with `Ctrl+C` and retry.

In native Expo tunnel mode, the runtime uses `https://<Expo-host>/__hairdoc_api/api/v1`; it accepts either Expo Go manifest host field so iOS never silently falls back to clear-text LAN HTTP. Metro forwards that prefix to local Django and rejects non-API paths. Tunnel calls allow normal cold-start latency and return explicit timeout/network errors. LAN/web development retains the detected private address. An explicitly hosted API wins, while a private HTTP override is intentionally bridged in tunnel mode. Production/EAS builds require an explicit hosted API URL.

## Database and Redis

For the zero-configuration foundation demo, Django falls back to a local ignored SQLite file. PostgreSQL is the project database and should be enabled before business-domain development.

Start the included local services:

```powershell
docker compose up -d
Copy-Item apps/backend/.env.example apps/backend/.env
.\.venv\Scripts\python.exe apps/backend/manage.py migrate
```

The compose PostgreSQL port is `5433` to avoid conflicting with an existing PostgreSQL installation on `5432`. Redis uses `6379`, and local config enables its Channels layer. Redis may run through the included Docker service or Ubuntu/WSL; Docker is not required when `redis-cli ping` already returns `PONG`. Start Redis before Django. Development probes Redis with a short timeout: if the port is missing or unresponsive, chat remains realtime within the single Django process through the in-memory Channels layer and Django prints a warning. Restart Django after Redis is healthy to exercise the production-like transport. Production settings require Redis and never fall back. Redis socket reads deliberately exceed Channels' blocking receive window so an idle healthy socket is not disconnected. The normal local launcher starts Django plus one Celery worker and beat scheduler so appointment reminders and optional delivery run with the app; all are stopped when the launcher exits.

To verify the shared realtime transport before opening both accounts:

```powershell
docker compose up -d redis
docker compose exec redis redis-cli ping
```

When using Ubuntu/WSL instead, `wsl redis-cli ping` must print `PONG`; then restart Django/`npm run dev`. The Windows Python process must also reach Redis; Ubuntu-only PONG does not prove this. The chat header says **Live** only after its authenticated WebSocket connects. Messages and inbox do not poll: history loads initially, older messages use cursor pagination on scroll, and sockets deliver live changes. User-scoped inbox/notification events include cache-ready data, so message sends/receives and typing do not refetch the lists. Reconnect/foreground events reconcile missed state.

If starting Expo manually instead of `npm run dev`, set `EXPO_PUBLIC_REALTIME_API_URL=http://<current-PC-LAN-IP>:8000/api/v1` before `expo start --go --tunnel`; the phone must be able to reach that LAN address. The app config also auto-detects a physical-adapter IP, but the explicit URL removes adapter ambiguity. The Expo tunnel carries REST through Metro, not the chat WebSocket.

Messaging history is durable in PostgreSQL. Text and image bubbles appear immediately on tap with a clock; acknowledgements reconcile by client UUID, and failed sends offer retry. While the authenticated socket is **Live**, validated text is persisted and broadcast through the same transaction service as REST. Private images use authenticated multipart REST before their socket event. Typing appears only with a live conversation socket. Replies are same-conversation only; either member may hide a message locally, and the sender may delete for everyone (tombstone plus private image removal). Each conversation is one client and TK. `/ws/v1/conversations/<id>/` and `/ws/v1/inbox/` use hashed, single-use 45-second tickets; the former checks membership and limits sends, the latter broadcasts user-scoped inbox/notification changes. In Expo tunnel mode REST uses the bridge, while `npm run dev` supplies the direct LAN socket URL; both devices must reach port 8000 for realtime. Sender state is clock, one tick for server-persisted, or two ticks for read—not delivery receipt. Images are metadata-stripped JPEGs behind short-lived signed paths and access logs. This is secure server-hosted messaging, not end-to-end encryption.

Notifications are persisted and user-scoped in PostgreSQL for messages, submitted consultations, appointment lifecycle/reminders, published care plans, and progress updates. The in-app centre/badge refresh from the user WebSocket and on app foreground; foreground remote banners are suppressed in favor of the in-app banner. Appointment times use each recipient’s timezone and dedupe keys prevent repeated alerts. Native background push uses `expo-notifications`, revocable per-device Expo tokens, privacy-safe previews, Celery retries, and allowlisted deep links. Expo Go cannot receive remote push; use a development/store build linked to an Expo project, then set `PUSH_NOTIFICATIONS_ENABLED=true` after APNs/FCM/EAS credentials exist. Closed-web-app browser push is not implemented and requires HTTPS/service-worker/VAPID design; do not represent it as working. iOS credentials require an Apple Developer account.

Email delivery is off by default and recorded separately from the in-app notification. Set `EMAIL_NOTIFICATIONS_ENABLED=true` and a real `DEFAULT_FROM_EMAIL` only after an approved sender/provider is configured. Development uses Django’s console email backend, so test messages appear in `.runtime/celery-worker.out.log`; no paid email service is assumed. For manual backend runs, start both `..\..\.venv\Scripts\python.exe -m celery -A config worker --pool=solo --loglevel=INFO` and `..\..\.venv\Scripts\python.exe -m celery -A config beat --loglevel=INFO` from `apps/backend`.

Never commit `.env`. Production settings reject an empty secret, empty allowed-host list, or non-PostgreSQL database.

Google Play also requires an external deletion resource. Host the Expo web build and submit its `/account-deletion` URL in Play Console; it sends signed-out users through web sign-in directly to the same three-step deletion flow. Final retention wording and periods must match the owner-approved Privacy Policy and applicable legal advice before store submission.

## Useful commands

Only three root scripts are maintained:

```powershell
npm run setup   # install Python and mobile dependencies
npm run dev     # run Django + Expo for a physical device
npm run check   # run all mobile and backend checks/tests
```

Mobile-only commands, from `apps/mobile`:

```powershell
npm run start
npm run android
npm run ios
npm run web
npm run lint
npm run typecheck
npm test
```

Backend-only examples, from the repository root:

```powershell
.\.venv\Scripts\python.exe apps/backend/manage.py check
.\.venv\Scripts\python.exe apps/backend/manage.py migrate
.\.venv\Scripts\python.exe apps/backend/manage.py test apps.core apps.accounts apps.content apps.consultations apps.payments apps.messaging apps.notifications apps.video apps.coaching apps.progress
.\.venv\Scripts\python.exe apps/backend/manage.py runserver 0.0.0.0:8000
```

## Repository layout

```text
apps/
  mobile/
    app/                    Expo Router routes
    src/providers/          root providers
    src/components/ui/      shared accessible primitives
    src/features/           vertical mobile features
    src/services/api/       API URL, client, and feature queries
    src/theme/              tokens, theme provider, motion
  backend/
    apps/accounts/          users, auth/sessions, profiles/preferences, legal/consent
    apps/core/              base model, middleware, errors, health API
    apps/content/           public backend-managed content
    apps/consultations/     services, intake, private photos, scheduling/booking, patient/staff workflows
    apps/messaging/         consultation conversations, durable messages, realtime tickets/Channels
    apps/coaching/          versioned plans, structured guidance, staff publishing, client reads
    apps/progress/          check-ins, private follow-up photos, comparison, expert feedback
    apps/notifications/     notification centre, reminders, email/push delivery lifecycle
    apps/video/             disabled default + dormant provider abstraction
    apps/payments/          orders, Stripe checkout/webhooks, receipts/refunds
    apps/private_media/     reusable private-file metadata and storage provider
    config/settings/        base, development, production
    requirements/
scripts/
  setup.ps1
  dev.ps1
  check.ps1
compose.yaml
PROJECT_PLAN.md
CURRENT_TASK.md
MASTER_AGENT_PROMPT.md
```

## Architecture rules

- TanStack Query owns server state; Zustand is reserved for small client-only state.
- React Hook Form + Zod will own form state and validation.
- Shared theme/UI/motion primitives prevent route-local design systems.
- Product UI contains only implemented user capabilities and real backend-managed content/state. Roadmap, deferred work, Admin publishing mechanics, and future-feature promises stay in the Markdown project records.
- Django owns authorization, workflow transitions, roles, prices, and object scope.
- REST is durable truth; Channels is only a realtime transport where needed.
- Public UUIDs supplement, but never replace, object-level authorization.
- Private files use an authorized storage abstraction, never public media URLs or database blobs; local private disk is development-only.
- Payment, video, storage, email, and push vendors stay behind interfaces.
- No new paid service may be introduced or enabled without explicit approval and cost review.
- Access tokens are never persisted. Native refresh tokens use SecureStore; web refresh tokens use only the backend-issued HTTP-only cookie and restore the session after reload.

Read `PROJECT_PLAN.md`, then `CURRENT_TASK.md`, before changing code. Stop after the current task; do not start the next feature automatically.
#   h a i r d o c - t k  
 
