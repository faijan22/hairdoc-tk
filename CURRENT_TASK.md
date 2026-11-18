# Current Task - 13L Stripe Test-Mode Activation

**Status:** `IN PROGRESS` — Stripe implementation and test API credential are ready; the stable staging DNS/server route, final signing secret and end-to-end payment acceptance remain.
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

## Remaining activation and acceptance

- Revoke the previously exposed Square tokens and remove legacy `SQUARE_*` lines from the ignored local `.env`; the application no longer reads them.
- Stripe test-mode secret key is configured in ignored `apps/backend/.env`; rotate it after development because it was shared through chat.
- Point `hairdoctk-dev.livecoder.tech` through Cloudflare to the staging server, create the ignored server `deploy/staging/.env`, run the first deployment, and verify HTTPS/WSS plus unchallenged signed POST delivery at `/api/v1/integrations/stripe/webhook/`.
- Correct/recreate the Stripe Sandbox destination with a current payload version, subscribe to the seven approved checkout/refund events, and put its final `whsec_...` value in ignored `apps/backend/.env` as `STRIPE_WEBHOOK_SECRET`.
- Apply migration `payments.0004_stripe_provider`.
- Complete one positive-price booking with a Stripe test card and verify payment, order, appointment, conversation, duplicate-event idempotency, failure/expiry, and refund records.
- Keep live credentials inactive; no real charge or production switch without explicit approval.

## Stop boundary

Do not switch to Stripe production or start Task 14 without approval.
