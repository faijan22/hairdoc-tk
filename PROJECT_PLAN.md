# HairDoc TK — Project Plan

Status legend: `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED`, `DEFERRED`.

## 1. Product objective and boundaries

Phase 1 must let a client discover and trust TK, purchase a consultation, complete the consultation journey, and continue coaching/follow-up in one app. The target journey is:

```text
Onboard → authenticate → explore TK/content → choose service → intake → private photos
→ choose slot → pay → confirmation/reminders → secure message/photo review → optional external call
→ published coaching plan → check-ins/photos → expert feedback → follow-up
```

The architecture is Phase-2-aware, but Phase 2 tables, endpoints, routes, jobs, and placeholder implementations are forbidden until that phase begins.

### Phase 1 — consultation business (`TODO`)

- Branded splash/onboarding and HairDoc hub.
- TK/TEDx, book, products, resources, promotions; authorized downloads only. Book/products link to external stores—no custom ecommerce.
- Email auth, verification/reset, Google/Apple sign-in, secure rotating sessions, role-aware routing.
- Profile, hair profile, timezone, notification preferences, legal/privacy/photo consent.
- Backend-managed consultation services and versioned dynamic intake forms with drafts.
- Private hair/scalp photos with validation, progress/retry, and signed access.
- Availability, timezone-safe slots, booking, reschedule/cancel, reminders, overlap protection.
- Consultation payments, history/receipt/refund state, signature-verified idempotent webhooks.
- Consultation-linked client↔TK messaging: text, attachment, read state, pagination, push; no social extras.
- Photo-first care; TK may arrange an external live call in Messages when needed. In-app managed video is deferred unless cost/privacy approval changes.
- Versioned coaching plans, structured recommendations/resources, private expert notes.
- Progress timeline, questionnaire, photos, comparison, expert feedback, follow-up.
- In-app, Expo push, and email notifications.
- Django Admin for catalogue/legal/configuration and developer fallback; role-gated app workspace for TK's frequent clinical review work.

### Phase 2 — planned, not implemented (`DEFERRED`)

- `PROFESSIONAL` onboarding, license verification, professional profiles/dashboard.
- Phoenix Hair Extensions training: catalogue, purchases, enrollments, modules/lessons, video/resources, progress, quizzes, live classes, certificates/verification.
- Extension HairSalons Hub: verified listings, specialties, location/search/filter, certification link, possible paid listing.
- Moderated community: groups, membership, posts, comments, reactions, reports, blocks, moderation. No unrestricted direct messaging by default.
- Subscriptions/memberships and entitlement-based access for training, coaching, directory, or premium features.
- WhatsApp notifications behind an adapter and explicit opt-in/cost approval.
- AI-assisted intake/history summaries, plan drafting, resource matching, and possible later image analysis; backend-only, feature-flagged, human-reviewed, never autonomous diagnosis.
- Optional custom admin/operations portal and ecommerce only if validated by actual needs.

## 2. Architecture

### System shape

```text
Expo mobile ── HTTPS `/api/v1` ── Django/DRF modular monolith ── PostgreSQL
     │                    │             │
     └──── WSS chat ──────┤             ├── Redis: Channels/Celery/cache/tickets
                          │             ├── private object storage
                          │             └── Celery workers
                          └── payment / video / Expo push / email adapters
```

- Django ASGI hosts HTTP and Channels. REST owns durable state; WebSockets broadcast authorized messaging events.
- One PostgreSQL database and initially one Redis deployment. Separate workloads only after measurement.
- Celery handles reminders, deliveries, receipts, file processing, and retries; synchronous requests remain bounded.
- Public API identifiers are UUIDs. Database relations, constraints, and backend authorization remain the security boundary.
- Mobile: Expo Router route groups; shared theme/UI primitives; feature folders; TanStack Query for remote state; Zustand only for small ephemeral/global client state; RHF+Zod for forms.
- No microservices, Kubernetes, Kafka, Elasticsearch, Firebase, separate chat vendor, or speculative Phase 2 scaffolds.

### Intended code boundaries

```text
mobile: app routes | features | components/ui | services/api | stores | schemas | theme
backend: core | accounts/consents | consultations/questionnaires | media | appointments
         payments | messaging | video | coaching/progress | content | notifications
         audit | integrations
```

Integrations expose narrow interfaces: `StorageProvider`, `PaymentProvider`, `VideoProvider`, `EmailProvider`, `PushProvider`; later `WhatsAppProvider`, `LLMProvider`. Domain services must not depend directly on a vendor SDK.

## 3. Phase 1 screen/state registry

These are product states, not a requirement for 82 separate route components. Reuse multi-step intake, content detail, upload, confirmation, and error-state shells.

| Area | Screens/states |
|---|---|
| Public/entry (1–14) | Splash; animated welcome; onboarding: TK, consultation/coaching, ecosystem; Get Started; Sign Up; Sign In; Email Verification; Forgot/Reset Password; Terms; Privacy; consultation disclaimer |
| Home/content (15–21) | Home; TEDx Detail; Book Detail; Products List/Detail; Resources List/Detail |
| Consultation (22–35) | Services; Service Detail; Start; intake steps: questionnaire, history, concerns, lifestyle/diet, products/routine, extensions, questions; consent-gated Photo Instructions/Upload; Review; Submitted; TK Queue/Case Review |
| Booking (36–42) | Choose Date; Choose Slot; Review; Confirmation; Appointment Detail; Reschedule; Cancel |
| Payment (43–48) | Checkout; Processing; Success; Failed; History; Receipt/Detail |
| Messaging (49–51) | Conversations; Consultation Conversation; Attachment Preview |
| Video (52–56) | Deferred managed-video states; no client CTA while provider is disabled |
| Coaching (57–61) | Plans; Plan Detail; Recommendation Detail; Recommended Products/Resources; Follow-up Instructions |
| Progress (62–68) | Journey/Timeline; New Check-in; Questionnaire; Photo Upload; Review; Detail; Before/After |
| Notifications (69–70) | List; contextual Detail |
| Profile/settings (71–82) | Profile/Edit; Hair Profile; Notification Preferences; Privacy/Consent; Sessions/Devices; Change Password; Data Export; Delete Account; Help; About; Logout Confirmation |

Client tabs: **Home · Consult · Messages · Visits · Profile**. TK tabs: **Home · Reviews · Messages · Schedule · Profile**. Both use the floating rounded bar only on top-level routes. Phase 2 navigation is controlled by disabled feature flags, not empty routes.

## 4. Backend domain/model registry

Fields below are architectural minimums, not final migrations.

| Domain | Phase 1 models and rules | Phase 2 extension |
|---|---|---|
| Identity | Custom `User`, `Role`, `UserRole`, `UserProfile`, `ClientHairProfile`; one identity; initial roles CLIENT/EXPERT/ADMIN | PROFESSIONAL/MODERATOR, `ProfessionalProfile` |
| Sessions | `DeviceSession` with hashed refresh token, family, expiry/revocation; hashed verification/reset tokens | Reused |
| Consent | Versioned `LegalDocument`, `UserConsent`; record exact accepted version | New policy types |
| Consultation catalogue | `ConsultationService`; server-owned duration/price/currency/status | Reused |
| Questionnaire | Versioned immutable `Questionnaire`, `QuestionnaireQuestion`, `QuestionOption`; typed/conditional configuration | Training quizzes may use related concepts, not forced reuse |
| Consultation | Central `ConsultationCase`, `ConsultationResponse`, `ConsultationAnswer`; server-controlled status transitions | AI summaries consume this domain |
| Files | `StoredFile` metadata/key/status + semantic links: `ConsultationPhoto`; short-lived signed access | Course files, certificates, licenses |
| Scheduling | `AvailabilityRule`, `AvailabilityException`, `Appointment`, `AppointmentStatusHistory`; UTC storage + timezone snapshots | Live training scheduling |
| Commerce | `Order`, `OrderItem`, `Payment`, `PaymentAttempt`, `Refund`, `WebhookEvent`; provider-neutral, server-calculated totals | `Subscription`, `Entitlement`, course/listing purchases |
| Messaging | `Conversation`, `ConversationMember`, `Message`, `MessageAttachment`; read cursor or `MessageRead` decided by measured needs | Possible reuse; community remains separate moderated domain |
| Video | `VideoSession`, `VideoParticipantEvent`; no permanent access tokens | Attach to `LiveTrainingSession` |
| Coaching | Versioned `CoachingPlan`, `CoachingPlanSection`, `Recommendation`; separate private `ExpertNote` | Subscription access if added |
| Progress | `ProgressCheckIn`, `ProgressResponse`, `ProgressPhoto` | Reused |
| Content | `ContentItem`, `ContentCategory`; types TEDX/BOOK/PRODUCT/RESOURCE/ARTICLE/PROMOTION; external URLs or authorized file | Training is a separate domain |
| Notifications | `Notification`, `NotificationDelivery`, `NotificationPreference`, `PushDevice`; safe preview text | WhatsApp channel |
| Platform | `AuditLog`, `FeatureFlag`, `AppSetting`; no secrets in JSON settings/audit metadata | Enables planned modules |

### Phase 2 model plan only

- Training: `Course → CourseModule → Lesson`; `User → Enrollment → LessonProgress/QuizAttempt → Certificate`; `Quiz/Question/Option`; `LiveTrainingSession`.
- Directory: `ProfessionalProfile`, `ProfessionalLicense`, `ProfessionalCertification`, `Specialty`, `DirectoryListing`, `ListingLocation`.
- Community: `CommunityGroup`, `CommunityMembership`, `CommunityPost`, `CommunityComment`, `CommunityReaction`, `ContentReport`, `ModerationAction`, `UserBlock`.
- Monetization: `Subscription`, `Entitlement`; payment/purchase grants explicit access instead of ad-hoc `payment.status` checks.

### Required data integrity/indexing

- Unique: normalized user email; `(user, role)`; `(conversation, user)`; `(provider, provider_event_id)`; `(case, plan_version)`; `(questionnaire, question_key)`.
- Checks: `ends_at > starts_at`; monetary amounts valid/nonnegative; refund positive and bounded; legal state transitions.
- Prevent overlapping active expert appointments transactionally/database-side. Never trust a previously displayed slot.
- Candidate indexes driven by endpoints: cases `(client/status/created)`, appointments `(expert/start/status)` and `(client/start/status)`, messages `(conversation/created/id)`, notifications `(user/read/created)`, payments `(user/status/created)`, progress `(case/submitted)`, content `(type/status/order)`.
- Avoid giant JSON records, uncontrolled generic foreign keys, universal soft deletion, and speculative indexes. Use JSONB only for genuinely dynamic values/configuration.

## 5. Phase 1 API registry

All paths are under `/api/v1/`; trailing slashes follow project convention. Errors use stable `error.code`, safe message/details, and request ID. Server owns prices, roles, object scope, and workflow transitions.

```text
AUTH     POST auth/register | login | refresh | logout | logout-all
         POST auth/email/verify | email/resend
         POST auth/password/forgot | reset | change | auth/google | auth/apple

ACCOUNT  GET/PATCH me | me/hair-profile | me/notification-preferences
         GET me/sessions | DELETE me/sessions/{id} | POST me/sessions/revoke-all
         GET/POST me/consents | POST me/export | me/delete-request
         POST me/push-devices | DELETE me/push-devices/{id}

APP      GET home | config | legal | legal/{type}/current
CONTENT  GET content | content/{id} | POST content/{id}/download

CONSULT  GET consultation-services | consultation-services/{id}
         GET/POST consultations | GET consultations/{id}
         POST consultations/{id}/submit | cancel
         GET consultations/{id}/questionnaire | GET/PATCH consultations/{id}/answers
FILES    GET/POST consultations/{id}/photos  [local backend transfer in development]
         POST consultations/{id}/photos/submit
         DELETE consultations/{id}/photos/{photo}
         GET private-files/photos/{photo}?token=...  [5-minute signed read]
STAFF    GET staff/consultations?limit={1..100} | staff/consultations/{id}

BOOKING  GET availability | availability/slots
         GET/POST appointments | GET appointments/{id}
         POST appointments/{id}/reschedule | cancel
         GET/PATCH staff/availability/weekly
         GET/POST/DELETE staff/availability/exceptions[/id]
         GET staff/appointments

PAYMENT  POST orders | orders/{id}/checkout
         GET payments | payments/{id}
         GET staff/payments | staff/payments/{id}
WEBHOOK  POST integrations/{provider}/webhook  [signature, replay and idempotency protected]

CHAT     GET conversations | conversations/{id}
         GET/POST conversations/{id}/messages (JSON text or multipart text/image)
         POST conversations/{id}/messages/{message_id}/delete (self/everyone)
         POST conversations/{id}/read | GET signed private message image
REALTIME POST realtime/ticket; WSS /ws/v1/conversations/{id}/ (typing, text send, read/deletion events)

VIDEO    GET appointments/{id}/video
         POST appointments/{id}/video/join | events | complete
COACH    GET consultations/{id}/plans | plans/{plan_id}
         GET/POST staff/consultations/{id}/plans
         GET/PATCH staff/plans/{plan_id} | POST staff/plans/{plan_id}/publish
PROGRESS GET/POST consultations/{id}/progress
         GET/PATCH progress/{checkin} | POST progress/{checkin}/submit
         GET/POST progress/{checkin}/photos | DELETE .../photos/{photo}
         GET staff/progress | staff/progress/{checkin}
         PATCH staff/progress/{checkin} | POST .../{checkin}/publish

NOTICE   GET notifications | notifications/{id}
         POST notifications/{id}/read | notifications/read-all
PUSH     GET/POST push-devices | DELETE push-devices/{id}
SUPPORT  POST support/contact (only if needed; otherwise expose safe contact config)
```

Rules: client lists/details start from user-scoped querysets; clients cannot PATCH statuses; cursor pagination for messages/notifications/timelines; bounded page pagination elsewhere; allowlisted filters/orderings; list serializers remain narrow; `home` aggregates through existing selectors without duplicating rules; direct-to-storage upload uses request→upload→complete.

## 6. Security and privacy policy

- Treat hair/scalp images, intake responses, coaching data, contact data, tokens, and private messages as sensitive. Collect only necessary data; document retention/deletion/export behavior before launch.
- HTTPS/WSS only outside local development. Secrets remain server-side and outside git/logs/mobile bundles.
- Short-lived access tokens plus rotating refresh tokens are implemented: native refresh tokens use platform secure storage, web is memory-only, device sessions are revocable, and refresh reuse revokes the family.
- Social login identity tokens are verified by the backend. Email verification/reset tokens are short-lived, single-use, and stored hashed.
- WebSockets use a 30–60-second, single-purpose ticket or equivalent secure handshake; never put refresh tokens in URLs. Check `ConversationMember` before accept and every privileged action.
- Every API defines role, object, field, and transition permission. Frontend hiding is not authorization. Admin access uses least privilege and MFA where available.
- Validate MIME by content, size, count, ownership, and category; private buckets only; short-lived URLs; strip EXIF/create safe variants where required; never log URLs/tokens/private answer bodies.
- Verify webhook signatures against raw bodies; unique event IDs, replay protection, idempotent processing. Payment totals originate on server.
- Apply rate limits/brute-force defense to auth, tickets, uploads, messaging, support, password reset, downloads, and join-token creation.
- Validate all inputs, escape rendered content, use secure headers/CORS/CSRF configuration appropriate to each client, dependency scanning, encrypted backups, and restore tests.
- Audit meaningful events: consent, consultation submission/view, private-file access, plan publish, role change, booking change, refund, export/delete. Keep audit metadata minimal and immutable.
- Do not present the app or AI output as diagnosis; publish client-approved legal/medical disclaimers and escalation guidance.

## 7. Integrations and cost-control policy

| Need | Phase 1 decision | Cost posture |
|---|---|---|
| Database | PostgreSQL | Open-source; pay only hosting/operations |
| Redis | Channels, Celery, cache/rate limit, realtime tickets | One instance initially |
| Files | Private S3-compatible object storage | Metadata in DB; compare storage/egress/backup cost |
| Chat | Django Channels + PostgreSQL | No chat SaaS initially |
| Push | Expo Push | Store per-device tokens; process receipts |
| Email | Elastic Email transactional HTTPS API v4 behind Django's email backend | API key stays server-side; low-volume auth/care delivery; recheck plan limits before production |
| Video | `DisabledVideoProvider`; photo/intake/message first, external call arranged manually when needed | $0 app video cost; dormant adapter cannot be enabled or billed without approval |
| Payments | Stripe-hosted Checkout behind `PaymentProvider` | No monthly/API fee; Stripe processing fee per transaction; verify TK account/country and current rate before launch |
| TEDx/book/products | Official watch/external buy links; signed download only for TK-authorized files | No video proxy or ecommerce platform |
| WhatsApp/AI | Disabled Phase 2 | Explicit approval and usage caps required |

**Hard rule:** do not add or enable a paid SaaS/API/cloud/database/storage/auth/chat/monitoring dependency without approval. A proposal must state necessity, ability of the current stack to cover it, free/open-source alternative, recurring cost/limits, security/data implications, lock-in/migration path, and shutdown cap. Pricing/free tiers must be reverified before provider selection and production launch.

Build normal product logic in the existing stack. Buy managed infrastructure where payment, video, push, email delivery, or object storage reliability/security would cost more to operate safely. Never optimize cost by weakening privacy, backups, payment integrity, or call reliability.

### Deployment environments

| Environment | Public origin | Purpose |
|---|---|---|
| Local | LAN/Expo development bridge | Developer-only iteration |
| Staging | `https://hairdoctk-dev.livecoder.tech` | Owner-server deployment, Stripe test mode, TestFlight/device acceptance; synthetic/test data only |
| Production | `https://api.hairdoctk.com` | Client-owned domain, live credentials and real patient data after release hardening |

Staging will initially run on the owner's server behind Cloudflare with Full (strict) TLS. Add a dedicated staging Django settings module rather than exposing `development` or weakening `production`: require a strong secret, PostgreSQL, healthy Redis Channels, HTTPS/WSS, explicit hosts/origins, secure cookies, consent enforcement and Stripe **test** credentials. The staging Stripe endpoint is `/api/v1/integrations/stripe/webhook/`; Cloudflare/reverse-proxy rules must preserve the raw request body and `Stripe-Signature` header and must not challenge that path.

Before deployment, add a reproducible backend container/release definition for the ASGI server, migrations/static collection and health checks; run PostgreSQL, Redis and background workers with persistent state and restart policies; keep secrets outside images/source; and configure encrypted database backups plus a restore check. Private media may use a non-public persistent server volume only for staging test data. Real patient photos require the approved private object-storage provider, retention policy, backups and access audit before production. Mobile/TestFlight builds must use the explicit staging HTTPS/WSS origins rather than LAN, Expo tunnel or Metro bridge discovery.

## 8. Progress registry

| # | Vertical slice | Status | Exit outcome |
|---:|---|---|---|
| 01 | Project + mobile theme/motion + Django base | `DONE` | Both apps boot; health endpoint; reusable visual foundation; no auth flow |
| 02 | Onboarding/content shell | `DONE` | Branded entry flow and backend-managed public content path |
| 03 | Authentication/sessions | `DONE` | Secure email/session lifecycle, recovery, device revocation, and protected routing |
| 03B | Google/Apple sign-in | `DEFERRED` | Phase 1 requirement awaiting owner-supplied provider IDs/credentials; no unsafe placeholder |
| 04 | Profile/consent | `DONE` | Grouped settings, editable profiles/preferences, security reuse, admin-versioned legal copy and exact-version consent |
| 05 | Consultation catalogue/intake | `DONE` | Dynamic versioned draft/review/intake-completion journey |
| 06 | Private uploads | `DONE` | Consent-gated private patient upload + TK in-app review workflow |
| 07 | Availability/booking | `DONE` | Transaction-safe timezone-aware appointment lifecycle |
| 07B | Home/consultation activation | `DONE` | Real aggregated home state and correct post-auth landing |
| 08 | Payment | `DONE` | Server-priced provider-neutral checkout, verified webhook, history/refunds |
| 09 | Messaging | `DONE` | Durable REST history/read/send + secure WSS; Expo-tunnel polling fallback |
| 09C | Messaging completion | `DONE` | One-client/TK real-time text/image chat, `Sent`/`Read`, conventional keyboard-safe composer, in-app alerts, and privacy-safe Expo push pipeline |
| 09B | Journey readiness/account control | `DONE` | DEBUG-only coherent preview; uploaded legal files; guarded account deletion and external web path |
| 10 | Video | `DEFERRED` | TK declined extra video cost; photo-first care and secure Messages are live; dormant adapter retained only for future approval |
| 10B | Product alignment | `DONE` | Provider-neutral payment seam; video disabled by default; HairDoc palette, role-clear homes, and floating navigation shipped |
| 10C | Web runtime/motion polish | `DONE` | Native notification APIs are web-gated; SF Pro web stack and reduced-motion-aware transitions verified |
| 10D | Navigation/feedback polish | `DONE` | Theme-safe transitions, travelling tab indicator, safe Settings back, green accents, and padded feedback shipped |
| 10E | Product-only UI cleanup | `DONE` | Removed unbuilt promises/settings and development/Admin language from user surfaces; roadmap is Markdown-only |
| 10F | Reference-led public UI redesign | `DONE` | Reference-derived hierarchy, restrained sage/forest system, modern type, soft surfaces, onboarding/auth/Home compositions, and integrated nav verified across platforms |
| 10G | Physical-iPhone API reliability | `DONE` | Expo Go tunnel-host fallback, realistic tunnel timeouts, explicit network errors, and live public bridge verification |
| 10H | Authenticated Home data repair | `DONE` | Preview response invariant restored, existing local case repaired, and legacy-null mobile parsing made resilient |
| 10I | Real local consultation flow | `DONE` | Real catalogue/account/availability/free-booking/photo path active; development records no fake consent while production still requires owner-approved copy |
| 10J | Form keyboard safety | `DONE` | Every current mobile input path scrolls/resizes above the keyboard; modal/chat exceptions are explicitly handled and regression-tested |
| 10K | Intake resume integrity | `DONE` | Saved choice/Boolean values rehydrate, every answered step value persists, untouched answers cannot be erased, and completed intake routes cannot reopen editing |
| 11 | Coaching | `DONE` | Assigned TK drafts/publishes immutable versioned client guidance; migration ships with development startup |
| 12 | Progress | `DONE` | Real check-ins, consented photos, baseline comparison, TK feedback, tests, and live PostgreSQL migrations complete |
| 13 | Care notifications | `DONE` | Durable in-app centre/realtime badge, session-bound multi-device Expo push, lifecycle cleanup, timezone reminders, external-alert preferences, and receipt audit |
| 13B | Public entry redesign | `DONE` | Art-directed responsive landing, intentional light brand theme, and authenticated consultation catalogue at UI/API boundaries |
| 13C | Sign-in/navigation polish | `DONE` | Accessible password reveal and deterministic Home return from Consult, Messages, and Visits root headers |
| 13D | Tunnel-save interaction repair | `DONE` | Expo-tunneled web uses the secure local API bridge and shared loading buttons remain visually stable |
| 13E | Role-aware messaging empty state | `DONE` | TK and clients receive distinct, accurate inbox guidance and relevant next actions |
| 13F | Realtime messaging interaction | `DONE` | Optimistic text/image sends, typing presence, stable images, sent/read ticks, and active-chat notification suppression over Channels/Redis |
| 13G | SDK 57 + intake resume repair | `DONE` | SDK 57 physical-client compatibility plus deterministic Boolean/choice persistence and hydration |
| 13H | Realtime chat reliability + inbox UX | `DONE` | Bottom-anchored live timeline, visible typing, immediate reconciliation, overlapping read ticks, modern inbox rows, unread tab dot, aligned composer, and safe local Redis fallback |
| 13I | Live chat + web session interaction repair | `DONE` | Stable Redis WebSockets, animated typing bubble, Enter/Next/submit controls, registration password reveal, HTTP-only web refresh cookie, and valid notification actions |
| 13J | Direct realtime chat delivery | `DONE` | Authenticated socket text persistence/broadcast, immediate two-client reconciliation, guaranteed-visible typing presence, and idempotent REST fallback |
| 13K | Chat interaction and message controls | `DONE` | No polling; cursor history, member-specific inbox and notification socket payloads update UI cache without repeated GETs, typing refreshes while active, and instant bubbles/replies/deletion pass automated checks; repeat physical acceptance during release hardening |
| 13L | Stripe test-mode activation | `IN PROGRESS` | Stripe Checkout and signed event/refund handling replace Square behind the provider seam; add test secrets outside source control, migrate, and verify checkout/webhook persistence end-to-end; no live-charge test without explicit approval |
| 14 | Phase 1 hardening/release | `TODO` | Security, accessibility, performance, observability, backup/restore, store builds |
| P2 | Training/directory/community/subscriptions/AI/WhatsApp | `DEFERRED` | Separate approved Phase 2 plan |

Only one row may be `IN PROGRESS`. Details and file limits live in `CURRENT_TASK.md`. On completion: verify acceptance, mark row `DONE`, add material ADRs, update README if commands/config changed, and replace `CURRENT_TASK.md` with the next approved slice only—do not start it automatically.

## 9. ADR log

| ADR | Decision | Status/rationale |
|---|---|---|
| 001 | Expo + TypeScript mobile stack and Expo Router | Accepted; cross-platform, file routing, shared foundation |
| 002 | Django/DRF modular monolith, PostgreSQL, `/api/v1` | Accepted; relational integrity, admin, low operational complexity |
| 003 | Redis shared initially by Channels/Celery/cache/tickets | Accepted; split only from measured capacity/security needs |
| 004 | Phase-2-aware boundaries, no Phase 2 implementation | Accepted; preserves growth without speculative code/schema |
| 005 | One custom User with roles/profiles | Accepted; avoids fragmented identities |
| 006 | REST source of truth; Channels only where realtime adds value | Accepted; no paid chat vendor in Phase 1 |
| 007 | Private object storage through abstraction/direct signed transfer | Accepted; scalable and safer than DB/server-disk blobs |
| 008 | Provider abstractions for payment/video/email/push/storage | Accepted; limit lock-in; vendor chosen/rechecked near integration |
| 009 | Managed video first; self-host only after economic/operational review | Accepted; call reliability is revenue-critical |
| 010 | Django Admin for Phase 1 operations | Accepted; avoids custom-admin cost |
| 011 | External commerce links for book/products | Accepted; no inventory/cart/fulfilment scope |
| 012 | TanStack Query server state; Zustand small client state; RHF+Zod forms | Accepted; clear ownership and validation |
| 013 | Public UUIDs plus strict authorization | Accepted; UUIDs are not an authorization substitute |
| 014 | Secure rotating device-session architecture | Accepted/implemented in Slice 03; one-time opaque refresh records detect reuse and revoke the family |
| 015 | Paid services require explicit approval and cost review | Accepted; prevents silent recurring bills |
| 016 | Expo SDK 57 stable + Django 5.2 LTS for the foundation | Superseded by ADR 031 for physical-iPhone Expo Go compatibility; Django 5.2 LTS remains accepted |
| 017 | SQLite is allowed only for zero-config foundation smoke tests; PostgreSQL remains the project database | Accepted; local compose uses port 5433 and must be enabled before business-domain work |
| 018 | Local device launcher detects the active LAN IP, binds/allowlists Django on it, permits local web origins, and injects Expo's API URL | Accepted; avoids hard-coded developer IPs and proves phone-to-backend communication |
| 019 | Onboarding completion stays local; public ecosystem content stays publishable in Django Admin | Accepted; avoids identity coupling and hard-coded/fake TK links |
| 020 | Expo Router routes live only in `apps/mobile/app`; `src/app` is forbidden | Accepted; Expo otherwise selects the wrong route root and serves stale/unmatched routes |
| 021 | Native auth persists only opaque refresh tokens in Expo SecureStore; access JWTs stay in memory and web auth is memory-only | Superseded by ADR 077 for web refresh continuity; native SecureStore and memory-only access JWT decisions remain accepted |
| 022 | Email verification/reset tokens are random, single-use, expiring, and hashed at rest | Accepted; DEBUG may return a local test token, production sends it only by email |
| 023 | Cormorant Garamond Semibold is bundled only for web and applied only to display headings at desktop width | Superseded by ADR 040; the editorial face and warm decorative system made the product feel template-generated rather than like a focused care app |
| 024 | Onboarding artwork and copy regions have stable dimensions | Accepted; all three steps measure at identical vertical positions while remaining scrollable for accessibility scaling |
| 025 | Google/Apple sign-in is deferred until real provider IDs/credentials are supplied | Accepted; no fake buttons, unverified tokens, or speculative provider configuration |
| 026 | DRF scoped throttles are defense-in-depth, not the production brute-force boundary | Accepted; production still requires proxy/edge rate limiting because DRF cache throttles are non-atomic |
| 027 | Do not force-fix current Expo/Metro `image-size`/`uuid` audit findings | Accepted temporarily; advisories are transitive build-tool findings, `image-size` has no patched release, and npm's proposed fix downgrades Expo; monitor before release |
| 028 | Settings uses labeled grouped cards and focused detail routes | Accepted/implemented in Slice 04; mirrors the approved hierarchy, keeps one canonical `/settings` entry, and reuses password/session controls instead of duplicating them |
| 029 | Profile/preferences and versioned legal consent remain in the accounts boundary for Slice 04 | Accepted/implemented; one-to-one user data stays user-scoped, Django Admin owns approved legal copy, and consent records the exact published version; split only if domain growth warrants it |
| 030 | Root checks must fail on any native command exit code | Accepted/implemented; Windows PowerShell 5 does not reliably honor `ErrorActionPreference` for native failures, so each lint/test/check step is explicitly asserted |
| 031 | Pin Expo SDK 54 while physical-iPhone Expo Go supports only SDK 54 | Superseded by ADR 038 after the App Store Expo Go advanced to SDK 57 |
| 032 | Settings writes use persistent success feedback; preference toggles update optimistically; global sign-out requires confirmation | Accepted/implemented; removes ambiguous repeat submissions, web toggle flicker, and accidental revocation of the current session |
| 033 | Consultation start locks service terms, client context, and one immutable questionnaire version; intake completion is distinct from final photo-backed submission | Accepted/implemented in Slice 05; preserves historical truth, supports safe Admin evolution, prevents client-owned pricing/status, and leaves private files isolated for Slice 06 |
| 034 | TK's frequent consultation/photo review belongs in the role-gated app, while Django Admin remains catalogue/legal/configuration and developer fallback | Accepted/implemented in Slice 06; mobile review scales better than raw tables, while `is_staff` plus object/status checks remain the server boundary; partially supersedes ADR 010 |
| 035 | Development photos use normalized JPEG files under ignored private local storage plus DB metadata behind `StorageProvider`; production moves to private object storage without changing consultation rules | Accepted/implemented in Slice 06; keeps local testing free and physical-device compatible, strips source metadata, avoids public media URLs, and retains the ADR 007 production direction |
| 036 | Availability is authored by TK in-app as local weekly intervals plus dated block/extra exceptions; clients receive only server-generated timezone-localized slots | Accepted/implemented in Slice 07; one source of truth handles service duration, timezone conversion and DST gaps without trusting client timestamps |
| 037 | Booking serializes on the expert row and revalidates the chosen slot inside the transaction; payment-pending holds expire after 30 minutes | Accepted/implemented in Slice 07; prevents overlapping active appointments and avoids falsely confirming unpaid bookings; Task 08 will confirm payment through verified provider events |
| 038 | Track the current physical-iPhone Expo Go SDK and upgrade Expo incrementally as its App Store runtime advances | Superseded by ADR 039; Expo's generic latest-SDK page was not evidence that its App Store iPhone runtime had advanced |
| 039 | Keep Expo SDK 54 until Expo explicitly ships a newer App Store Expo Go runtime or the project adopts an approved iOS development-build path | Superseded by ADR 073 after the user's installed physical-device client required SDK 57 |
| 040 | Use native system typography and a restrained neutral/deep-green visual system across mobile and web | Partially superseded by ADR 042 for color direction; the native typography, compact layout, keyboard safety, and responsive foundation remain accepted |
| 041 | Dynamic Expo app config detects the active physical LAN API URL for local non-EAS development; explicit environment configuration wins | Accepted/implemented; manual tunnel starts no longer mistake Expo's tunnel hostname for Django, while production/EAS remains explicit |
| 042 | Use neutral surfaces with a restrained violet/rose accent pair, purposeful reduced-motion-aware onboarding, and a dashboard derived only from real consultation/appointment/content state | Superseded by ADR 053; real dashboard/motion rules remain accepted |
| 043 | Native local-development API calls use a Metro bridge when Expo Go runs through `exp.direct`; direct LAN remains a fallback and hosted API configuration wins | Accepted/implemented; the temporary tunnel exposes only `/api/v1`, preserves Django authorization, avoids iOS local-HTTP failures, and is excluded from production/EAS architecture; extends ADR 041 |
| 044 | Home is a server-composed read model built from existing publication, consultation, booking-expiry, and object-scope rules; sign-in lands on Home | Accepted/implemented; reduces dashboard request fan-out without duplicating domain transitions and makes Explore the canonical post-auth entry |
| 045 | Stripe-hosted Checkout is the approved Phase 1 payment adapter; webhook state is the fulfillment authority | Superseded by ADR 051 after TK confirmed Square; provider-neutral records and webhook authority remain accepted |
| 046 | PostgreSQL is messaging truth; authenticated/idempotent REST persists before Channels broadcast; production Redis only fans out realtime events | Partially superseded by ADR 078 for live text writes; ticket authorization, PostgreSQL truth, Redis fan-out, private-image REST writes, and bounded fallback polling remain accepted |
| 047 | Local journey visibility uses one idempotent DEBUG-only bootstrap command, not production fixtures or fake checkout logic | Superseded by ADR 060; even clearly labelled preview domain records leak implementation scaffolding into the real product experience |
| 048 | Client account deletion immediately removes recoverable login/profile/auth/private-file/intake/message data and de-identifies the inactive audit tombstone | Accepted/implemented; password plus exact typed confirmation and explicit acknowledgement prevent one-tap loss, all sessions are removed, staff ownership fails closed, and the public web path supports Google Play's external-resource requirement; final retention periods remain a legal-policy prerequisite |
| 049 | Daily is the initial managed video adapter; calls use private two-person rooms and backend-issued appointment-scoped expiring grants, while Expo Go opens Daily Prebuilt in a secure provider window | Superseded by ADR 052; adapter remains dormant but is not the active product path |
| 050 | Consultation chat is exactly one client and one TK, with PostgreSQL truth, sender-visible `Sent`/`Read` only, private normalized image attachments, and notification delivery kept separate from message state | Accepted/implemented; Channels/Redis provides active real-time updates, tunnel mode safely polls, in-app notices work in Expo Go, and privacy-safe Expo push activates only in credentialed development/store builds |
| 051 | Square-hosted Payment Links replace Stripe | Superseded by ADR 082 after the owner changed the selected payment provider; provider-neutral records and webhook authority remain accepted |
| 052 | Consultations are photo-first; `DisabledVideoProvider` is the default and TK arranges an external call through Messages only when useful | Accepted/implemented; creates no video bill or account requirement, removes the in-app CTA, and retains a dormant provider seam; supersedes ADR 049 |
| 053 | Use HairDoc's warm ivory/sage/deep-forest palette with restrained burgundy, native mobile type, web-only editorial headings, role-specific homes, and a floating five-tab bar | Partially superseded by ADR 055; layout, role, and navigation direction remain accepted |
| 054 | Web uses an SF Pro Display/Text system stack and never initializes native notification listeners; shared route motion must honor reduced-motion preferences | Accepted/implemented; fixes the Expo Notifications web crash, avoids redistributing Apple's proprietary font, and gives navigation consistent restrained feedback |
| 055 | Navigator scenes remain opaque and theme-matched; decorative UI uses green/sage, red is danger-only, and the floating tab bar owns one travelling active indicator | Accepted/implemented; prevents white transition flashes and rounded-edge seams while giving destination changes continuous feedback; supersedes ADR 053's burgundy accent |
| 056 | Development roadmap and unbuilt features never appear in product UI | Accepted/implemented; future/deferred work stays in Markdown only, while UI exposes implemented actions, real backend state, and neutral user-facing empty states |
| 057 | Owner references guide spacing, hierarchy, shape, and interaction—not literal screen copying or their multicolor palettes | Accepted/implemented; use modern system typography, consistent 20px gutters, soft filled modules, minimal borders, and one restrained forest/sage accent while compositions remain HairDoc-specific and backend-driven |
| 058 | Expo Go native API resolution accepts both manifest `hostUri` and Expo Go `debuggerHost`; tunnel calls receive a 20-second budget | Accepted/implemented; prevents iOS native fetch from falling back to blocked clear-text LAN HTTP and avoids false offline errors during tunnel startup/latency while retaining explicit hosted API precedence |
| 059 | Every consultation case should own a questionnaire response; mobile remains tolerant of legacy null questionnaire versions | Accepted/implemented; new cases preserve the domain invariant, and one malformed legacy optional label can no longer blank the complete authenticated Home payload |
| 060 | Local development uses the real backend workflow and owner-managed domain records; no seeded preview consultation/payment/conversation exists | Accepted/implementing; Django Admin owns genuine TK-approved services and questionnaires, clients create real cases through the API, Stripe test mode is the only test-payment path, and roadmap/demo labels never appear in product state; supersedes ADR 047 |
| 061 | Zero-priced consultation booking confirms server-side without creating an order/payment or contacting the payment provider | Accepted/implemented; free services bypass checkout, confirmation and two-member conversation creation remain atomic, while any positive server-snapshotted price retains the verified provider path |
| 062 | TK photo reviews and payment records are scoped by the consultation service's assigned expert, not by staff status alone | Accepted/implemented; TK receives a backend-driven latest-upload home entry and dedicated payment list/detail while unrelated staff accounts receive no records, preserving least privilege as staff roles expand |
| 063 | Coaching plans are consultation-bound, assigned-expert-authored, draft-private, and immutable after publication | Accepted/implemented; TK manages structured sections/recommendations in-app, clients read only their own published versions, and changed guidance becomes a new auditable version |
| 064 | Progress is a care-plan-gated, consultation-bound client submission with consented photos and separately published expert feedback | Accepted/implemented; one server-owned draft is editable until submission, assigned TK sees baseline/follow-up images, unpublished feedback stays private, and publication locks the review |
| 065 | Shared mobile screens are keyboard-aware by default, with dedicated avoidance for modal and fixed-composer inputs | Accepted/implemented; iOS adjusts scroll insets, Android resizes/avoids by height, chat owns its composer behavior, and a source-level regression test covers future form screens |
| 066 | Local development may bypass photo consent solely to exercise the real private upload pipeline; production forces exact-version consent | Accepted/implemented; bypassed photos have nullable consent audit fields and no fabricated acceptance, while authorization, normalization, private storage, signed reads, access logging, ownership, and assigned-TK scoping remain unchanged |
| 067 | Intake editing is state-gated and patches only explicitly changed answers | Superseded by ADR 074; React Hook Form dirty tracking proved too fragile for step persistence, while the state-gating decisions remain accepted |
| 068 | PostgreSQL notifications are durable truth; category preferences gate event creation, dedupe keys make domain/reminder events idempotent, and channels remain independent delivery attempts | Accepted/implemented; clients and assigned TK receive scoped in-app updates, reminder copy uses the recipient timezone, email/push contain no sensitive care content, allowlisted routes prevent arbitrary deep links, Expo receipts revoke dead devices without inventing a user-visible Delivered state, and providers remain disabled until approved credentials exist |
| 069 | Signed-out Explore is an editorial account-entry surface; consultation catalogue/prices/details require authentication in both mobile routing and the API | Accepted/implemented; removes the confusing public working flow, keeps only genuinely public TK content public, uses a fixed light HairDoc palette for Phase 1 consistency, and gives mobile/web dedicated responsive compositions rather than stretching the authenticated dashboard |
| 070 | Floating-tab root header chevrons target Home explicitly; detail headers use history with a safe route fallback | Accepted/implemented; tab replacement does not guarantee a back-stack entry, so root actions must be deterministic and deep-linked details must never dispatch an unhandled back action |
| 071 | Web pages actually hosted on an Expo `exp.direct` tunnel use the same-origin development API bridge | Accepted/implemented; avoids browser mixed-content/private-network failures while localhost web stays direct, native tunnel behavior remains unchanged, and explicit hosted HTTPS APIs retain precedence |
| 072 | Chat keeps REST/PostgreSQL as durable truth while optimistic client state and Redis-backed Channels provide immediate interaction | Accepted/implemented; client-generated idempotency IDs reconcile sends, typing is ephemeral and member-scoped, signed image URLs stay stable per open screen, and only notifications for the currently visible conversation are suppressed |
| 073 | Target Expo SDK 57 and React Native 0.86 for the user's current physical-device runtime | Superseded by ADR 084 after the App Store Expo Go runtime advanced to SDK 58 |
| 074 | Intake steps persist every defined answer in the current section, not only fields reported dirty by the form library | Accepted/implemented; explicit `false` and selected options cannot be skipped, undefined controls remain omitted, server validation stays authoritative, and resume normalizes canonical control values before hydration |
| 075 | Development validates Redis responsiveness before selecting the channel layer; an unhealthy endpoint falls back only to the single-process in-memory layer | Accepted/implemented; prevents 10-second REST send stalls and sockets that connect then die during local testing, while a healthy Redis remains preferred and production still fails closed unless Redis Channels is configured |
| 076 | Redis channel connections use a read timeout longer than Channels' five-second blocking receive and send periodic application heartbeats | Accepted/implemented; redis-py 8 otherwise times out a healthy blocking read at the same boundary, causing Live→polling loops; verified against the owner's Ubuntu Redis after 6.5 seconds idle |
| 077 | Web refresh sessions use a rotating HTTP-only, scoped, SameSite cookie; access JWTs remain memory-only and native refresh tokens remain in SecureStore | Accepted/implemented; page refresh can restore a session without exposing the refresh secret to JavaScript or browser storage, custom client headers/CORS constrain cookie flows, and local web/API resolution remains same-site |
| 078 | Active sockets may persist validated text through the same transactional messaging service used by REST; image writes remain multipart REST | Accepted/implemented; membership/status checks, a 30/minute socket limit, 4,000-character bound, PostgreSQL commit-before-broadcast, and client UUID idempotency preserve security while removing the event→history-fetch delay; REST remains the safe retry path |
| 079 | Chat optimistic bubbles are local UI state until acknowledged; replies and deletion are durable server state | Accepted/implemented; clock/retry never waits for the network, pending bubbles survive background query refetch while the screen stays open, reply targets are conversation-scoped, personal deletion is viewer-specific, and sender-only shared deletion removes sensitive content/file while keeping a tombstone and broadcasting it |
| 080 | Chat history is cursor-fetched and sockets, not timed polling, drive live state | Partially superseded by ADR 081 for live cache updates; initial/reconnect/foreground catch-up, Expo tunnel REST/LAN socket split, and native/web push limits remain accepted. |
| 081 | User-scoped realtime events carry cache-ready inbox and notification payloads | Accepted/implemented pending device acceptance; each member receives only their own serialized conversation row and notifications, eliminating send/receive/read-triggered list GETs. Initial/reconnect/foreground REST remains the consistency boundary; typing presence is renewed over the socket until idle. |
| 082 | Stripe Checkout replaces Square behind the existing payment provider boundary | Accepted/implemented pending test-mode activation; test/live key prefixes are enforced, Stripe hosts card entry, signed timestamped events are fulfillment authority, server order/amount/currency metadata is revalidated, and historical Square rows remain readable without retaining an active Square adapter; supersedes ADR 051 and restores ADR 045's provider choice |
| 083 | The first hosted environment is isolated staging on the owner's server at `hairdoctk-dev.livecoder.tech`; production remains `api.hairdoctk.com` | Accepted/implemented pending server activation; dedicated fail-closed settings and Docker Compose run PostgreSQL, Redis, localhost-only Daphne/Channels and Celery behind the server's existing aaPanel Apache HTTPS proxy, with persistent staging volumes, Stripe test mode and one-command fast-forward deployment; this environment remains synthetic/test-data-only and cannot become production by swapping credentials |
| 084 | Align the mobile app to Expo SDK 58, React Native 0.88 and React 19.3 | Accepted/implemented; Expo-managed native dependencies are version-aligned, web remains explicitly static, Expo Doctor/type/lint/tests pass, and production bundles export for iOS, Android and web; supersedes ADR 073 |
| 085 | In-app notifications are durable product state and never require OS permission; preferences gate only push/email, while each Expo token belongs to one authenticated device session | Accepted/implemented; user-scoped Channels events update the active app, all valid signed-in devices may receive privacy-safe external alerts, logout/revocation/expiry/deletion deactivate delivery, hourly cleanup catches stale legacy sessions, and Expo receipts remove uninstalled/invalid devices; supersedes ADR 068's category-preferences-gate-event-creation rule |
| 086 | Elastic Email's transactional HTTPS API v4 is the Phase 1 email transport | Accepted/implemented pending credential activation; Django auth and care emails share one API-key backend, server-only `SendHttp` credentials and a verified sender replace SMTP username/password, stable idempotency keys protect retries, and the provider response remains delivery-attempt evidence rather than proof of inbox delivery |

Append rather than silently rewriting decisions. Superseded ADRs must link to their replacement.

## 10. Definition of done

A slice is done only when its mobile/API/admin path works as scoped; validation, authorization, migrations and relevant tests pass; loading/empty/error/retry/accessibility states are covered; no secrets/private data leak; related docs/progress/ADRs are current; and no next-slice work was started.
