import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { messagePageSchema } from "./messageSchemas.ts";

describe("message API contracts", () => {
  it("accepts bounded cursor history", () => {
    const id = "2f112577-1801-43e9-a36c-d2896f8aefb0";
    const page = messagePageSchema.parse({ next: null, previous: null, results: [{
      public_id: id, conversation_public_id: id, sender_public_id: id, sender_name: "TK",
      body: "Hello", attachment: null, status: "SENT", client_message_id: id, created_at: "2026-08-19T10:00:00Z",
    }] });
    assert.equal(page.results[0].body, "Hello");
  });

  it("rejects malformed realtime-shaped history", () => {
    assert.throws(() => messagePageSchema.parse({ results: [{ body: 42 }] }));
  });

  it("accepts reply context and a shared deletion tombstone", () => {
    const id = "2f112577-1801-43e9-a36c-d2896f8aefb0";
    const page = messagePageSchema.parse({ next: null, previous: null, results: [{
      public_id: id, conversation_public_id: id, sender_public_id: id, sender_name: "TK",
      body: "", attachment: null, status: "READ", client_message_id: id,
      created_at: "2026-09-18T10:00:00Z", deleted_for_everyone: true,
      reply_to: { public_id: id, sender_name: "Client", body: "", deleted_for_everyone: true, has_attachment: false },
    }] });
    assert.equal(page.results[0].deleted_for_everyone, true);
    assert.equal(page.results[0].reply_to?.deleted_for_everyone, true);
  });
});
