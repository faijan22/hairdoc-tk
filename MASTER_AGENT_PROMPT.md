# Compact Master Coding-Agent Prompt

You are implementing HairDoc TK in this repository.

Before every task, read in order:

1. `README.md` — actual setup and commands.
2. `PROJECT_PLAN.md` — scope, architecture, registries, security/cost rules, progress, ADRs.
3. `CURRENT_TASK.md` — the only authorized implementation slice.

Then inspect the repository, version-control status/diff, and relevant existing code. Search before creating: reuse or refactor the canonical path; do not add duplicate components, routes, models, APIs, config, styles, utilities, migrations, or parallel “new” implementations. Remove only stale code made obsolete by this task and only when ownership/safety is clear. Preserve unrelated user changes.

Rules:

- Work on exactly one vertical slice and only within `CURRENT_TASK.md`. Complete mobile/API/data/admin/tests/docs for that slice as applicable. Do not begin, scaffold, or “prepare” the next feature.
- `PROJECT_PLAN.md` plans the full product, but Phase 2 training/directory/community/subscriptions/AI/WhatsApp remains unimplemented until explicitly authorized.
- Follow the frozen stack and `/api/v1/`. Keep a modular monolith, clear feature/domain boundaries, provider interfaces, narrow APIs, backend-owned authorization/prices/state transitions, and private-data protections.
- During Task 01, define only the minimal custom-user schema required before Django's first irreversible migration. That schema-only foundation exception is not authorization to build auth UI, endpoints, tokens, device sessions, social login, or any authentication flow.
- Server data: TanStack Query. Small client-only state: Zustand. Forms: RHF+Zod. Theme/motion: shared tokens, Reanimated/Gesture Handler, accessibility and reduced motion.
- REST is durable truth; WebSockets are realtime transport only. Use public UUIDs plus real authorization. Keep private bytes in authorized object storage, not PostgreSQL/public URLs.
- Never introduce or enable a paid SaaS, API, cloud product, database, storage, auth, chat, monitoring, video, email, payment, AI, or WhatsApp service without explicit approval. First report necessity, current-stack option, free/open-source alternative, recurring cost/limits, security/data impact, and lock-in/migration path. Never weaken security to save money.
- Do not invent requirements, vendor commitments, placeholder Phase 2 code, speculative abstractions, or broad refactors. If a consequential ambiguity cannot be resolved from code/docs, stop and ask one concise question.
- Never expose the development roadmap in the product UI. Unbuilt, planned, deferred, or next-slice features belong only in `PROJECT_PLAN.md`/`CURRENT_TASK.md`; do not add teaser cards, disabled placeholders, settings, navigation, or promises for them. Empty states must describe the user's current state without mentioning Admin, publishing workflows, implementation progress, or future development.
- Preserve the owner-approved visual direction: modern native/system sans type, consistent 20px mobile gutters, deliberate whitespace, soft filled cards, minimal borders/shadows, and a restrained forest/sage accent with red reserved for danger. Reference images inform principles only; never copy their layouts or import their multicolor palettes.
- Use environment variables for secrets; never expose them to mobile bundles, logs, fixtures, docs, or commits. Apply validation, permissions, constraints, indexes, idempotency, rate limits, and audits in proportion to the active slice.
- Keep responses concise. Do the work and verification; do not narrate obvious steps or paste large files/diffs.

Completion protocol:

1. Run the checks required by `CURRENT_TASK.md`; inspect the final diff and search for duplicates/stale code/secrets. Never claim an unrun check passed.
2. Update README only when real setup/commands/config changed.
3. Mark the active row in `PROJECT_PLAN.md` `DONE` only when every acceptance criterion passes; update progress and append material ADRs without erasing history.
4. Record concise verification/deviations in `CURRENT_TASK.md`. Replace it with the next task only if the owner explicitly asked; otherwise leave the planned next slice unauthorized.
5. Report: outcome, key files, checks, blockers/deviations. Then stop. Do not start the next feature.
