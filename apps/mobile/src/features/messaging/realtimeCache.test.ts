import assert from "node:assert/strict";
import { test } from "node:test";

import type { Conversation } from "../../services/api/messaging.ts";
import type { CareNotification } from "../../services/api/notifications.ts";

import {
  applyNotificationReads,
  markAllNotificationsCachedRead,
  markNotificationCachedRead,
  upsertConversation,
  upsertNotification,
} from "./realtimeCache.ts";

const conversation = (id: string, updated_at: string) => ({
  public_id: id, updated_at,
  consultation_public_id: id, service_name: "Consultation", status: "ACTIVE",
  other_member_name: "TK", last_message: null, unread_count: 0,
  created_at: updated_at,
}) as Conversation;

const notification = (id: string, read_at: string | null = null) => ({
  public_id: id, kind: "NEW_MESSAGE", title: "New message", body: "You have a message.",
  route: "/messages/one", conversation_public_id: null, read_at,
  created_at: "2026-09-19T01:00:00Z",
}) as CareNotification;

test("inbox socket updates only the affected row and deduplicates it", () => {
  const old = conversation("one", "2026-09-18T10:00:00Z");
  const other = conversation("two", "2026-09-18T11:00:00Z");
  const latest = conversation("one", "2026-09-19T01:00:00Z");
  assert.deepEqual(upsertConversation([old, other], latest), [latest, other]);
  assert.deepEqual(upsertConversation(undefined, latest), undefined);
});

test("notification socket and read responses update counts without refetching", () => {
  const first = notification("one");
  const initial = { unread_count: 0, results: [] as CareNotification[] };
  const received = upsertNotification(initial, first)!;
  assert.equal(received.unread_count, 1);
  assert.equal(upsertNotification(received, first)?.unread_count, 1);
  const read = markNotificationCachedRead(received, notification("one", "2026-09-19T01:01:00Z"))!;
  assert.equal(read.unread_count, 0);
  assert.equal(markAllNotificationsCachedRead(received)?.unread_count, 0);
  const serverRead = applyNotificationReads(received, ["one"], "2026-09-19T01:02:00Z", 0)!;
  assert.equal(serverRead.unread_count, 0);
  assert.equal(serverRead.results[0].read_at, "2026-09-19T01:02:00Z");
});
