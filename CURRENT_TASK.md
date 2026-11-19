# Current Task - 13L Stripe Test-Mode Activation

**Status:** `IN PROGRESS` — Stripe Checkout and stable staging routing are active; correct webhook delivery and end-to-end payment acceptance remain.
**Started:** 2026-10-05
**Next planned, not started:** Task 14 hardening.

## Scope

- Replace Square with Stripe Checkout behind the existing provider boundary.
- Keep test and production credentials strictly separated and verify that webhook-confirmed payments persist and confirm appointments.

## Ready

- Server-priced Stripe-hosted Checkout; HairDoc TK never handles card data.
- Idempotent Checkout Session creation with HairDoc order references in Stripe metadata.
- Constant-time raw-body webhook verification with timestamp tolerance and replay-safe event storage.
- Amount, currency, order reference, Checkout Session, PaymentIntent, event ID, and refunds are validated before state changes.
- `test` rejects live keys; `production` rejects test keys and requires HTTPS return URLs.
- Free consultations bypass the provider; historical Square records remain readable but Square checkout/webhook code is removed.
- Payment-status refresh failures remain visible/retryable in the screen instead of becoming unhandled Expo promises; development logs identify only the failed method/path/status.
- Chat images open in a private full-screen pinch/pan viewer without blank black transition frames; long-press actions use a keyboard-safe bottom sheet with a selected-message preview, stable client-message keys prevent pending/sent/read reconciliation from remounting and blinking bubbles, and message corners follow compact modern chat geometry.
- Chat headers show peer presence—not local transport state: `Online` requires at least one active peer connection, while app background, screen lock, last-device disconnect, or socket loss returns it to `Offline`; typing temporarily takes priority.
- Mobile is aligned to Expo SDK 58 / React Native 0.88 for the current App Store Expo Go runtime; Expo Doctor, types, lint, 24 tests, and iOS/Android/web production exports pass.
- Physical-device image uploads use Expo SDK 58 `File`/`Blob` multipart bodies instead of the removed legacy React Native URI object; progress, consultation, and chat photos share the corrected upload path.
- Staff/client workspace boundaries are enforced in navigation and APIs: TK sees client-care tools instead of Hair Profile/My Appointments, client consultation routes redirect to staff workspaces, and staff accounts cannot create a client hair profile or start a self-consultation.
- A fail-closed staging deployment stack is ready for `hairdoctk-dev.livecoder.tech`: Docker Compose runs PostgreSQL, Redis, localhost-only Daphne/Channels, and Celery worker/beat behind the server's existing aaPanel Apache HTTPS proxy; server bootstrap and one-command Git/migration/restart deployment scripts are included.
- Notifications use two independent layers: durable in-app records and user-scoped realtime inbox events are always created, while push/email preferences gate only external alerts. Expo devices are session-bound, fan out across valid signed-in devices, and deactivate on device logout, logout-all, password/session revocation, account deletion, session expiry, or Expo's invalid-token receipt.
- Transactional email uses Elastic Email's HTTPS API v4 through a Django email backend, with API-key authentication, verified-sender enforcement by the provider, and stable idempotency keys for auth and notification deliveries; SMTP credentials are not required.
- Client payment refresh actively retrieves the existing user-scoped Checkout Session from Stripe and validates its order, amount and currency before confirming it, providing a bounded recovery path when a webhook is delayed or missed; it is rate-limited and removes continuous mobile polling.
- Care-plan acceptance is complete end to end: staff intake review renders questionnaire option labels instead of storage keys, publication shows an explicit locked/sent state, durable unread in-app notifications deep-link to the published plan, embedded HTTPS guidance links are tappable, and a newly confirmed empty client/TK conversation is broadcast into both cached inboxes before either person sends a message.

## Remaining activation and acceptance

- Revoke the previously exposed Square tokens and remove legacy `SQUARE_*` lines from the ignored local `.env`; the application no longer reads them.
- Stripe test-mode secret key is configured in ignored `apps/backend/.env`; rotate it after development because it was shared through chat.
- Correct the Stripe Sandbox destination from the obsolete, non-resolving `api-dev.hairdoctk.livecoder.tech` hostname to `https://hairdoctk-dev.livecoder.tech/api/v1/integrations/stripe/webhook/`, use a current payload version, subscribe to the seven approved checkout/refund events, and verify successful signed delivery in Stripe Event deliveries.
- Apply migration `payments.0004_stripe_provider`.
- Apply migration `notifications.0004_pushdevice_session`. External OS push remains intentionally disabled until an EAS project/development or store build has valid Apple/Android push credentials; then set `PUSH_NOTIFICATIONS_ENABLED=true`. Expo Go and web continue to receive the in-app realtime notification layer without OS push.
- Put the Elastic Email `SendHttp` API key in ignored staging environment configuration as `ELASTIC_EMAIL_API_KEY`, set the verified `DEFAULT_FROM_EMAIL`, enable `EMAIL_NOTIFICATIONS_ENABLED`, redeploy, and confirm a verification email plus one worker-delivered care notification in Elastic Email Activity.
- Complete one positive-price booking with a Stripe test card and verify payment, order, appointment, conversation, duplicate-event idempotency, failure/expiry, and refund records.
- Keep live credentials inactive; no real charge or production switch without explicit approval.

## Stop boundary

Do not switch to Stripe production or start Task 14 without approval.
