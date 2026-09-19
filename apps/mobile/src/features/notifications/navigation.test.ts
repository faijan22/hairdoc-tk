import assert from "node:assert/strict";
import test from "node:test";

import { safeNotificationHref } from "./navigation.ts";

const id = "3b86a8c2-5a51-4f75-934a-11bf968c5925";

test("allows only notification destinations owned by the app", () => {
  assert.equal(safeNotificationHref(`/messages/${id}`), `/messages/${id}`);
  assert.equal(safeNotificationHref(`/appointments/${id}`), `/appointments/${id}`);
  assert.equal(safeNotificationHref("/staff/appointments"), "/staff/appointments");
  assert.equal(safeNotificationHref(`/staff/consultations/${id}`), `/staff/consultations/${id}`);
  assert.equal(safeNotificationHref(`/plans/${id}`), `/plans/${id}`);
});

test("falls back for malformed or external destinations", () => {
  assert.equal(safeNotificationHref("https://example.com"), "/notifications");
  assert.equal(safeNotificationHref("/settings"), "/notifications");
  assert.equal(safeNotificationHref(undefined), "/notifications");
});
