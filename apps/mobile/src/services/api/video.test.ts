import assert from "node:assert/strict";
import test from "node:test";

import { videoStateSchema } from "./videoSchemas.ts";

test("video state rejects unsafe or incomplete provider data", () => {
  assert.throws(() => videoStateSchema.parse({ can_join: true }));
});

test("video state accepts a complete appointment-bound state", () => {
  const parsed = videoStateSchema.parse({
    appointment_public_id: "7c536f0a-0696-4d14-a74c-d70c7d260ad4",
    service_name: "Consultation",
    participant_role: "CLIENT",
    appointment_status: "CONFIRMED",
    session_status: "NOT_CREATED",
    starts_at: "2026-08-20T10:00:00Z",
    ends_at: "2026-08-20T10:30:00Z",
    available_from: "2026-08-20T09:50:00Z",
    expires_at: "2026-08-20T10:45:00Z",
    provider_configured: true,
    can_join: true,
    reason_code: "ready",
    message: "Ready",
  });
  assert.equal(parsed.participant_role, "CLIENT");
});
