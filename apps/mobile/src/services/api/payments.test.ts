import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { orderSchema, paymentSchema } from "./paymentSchemas.ts";

const id = "2f112577-1801-43e9-a36c-d2896f8aefb0";

describe("payment API contracts", () => {
  it("accepts server-owned order and receipt data", () => {
    assert.equal(
      orderSchema.parse({
        public_id: id,
        appointment_public_id: id,
        consultation_public_id: id,
        service_name: "Consultation",
        appointment_starts_at: "2026-08-20T09:00:00Z",
        status: "PENDING",
        status_label: "Pending payment",
        payment_public_id: null,
        payment_status: null,
        subtotal_amount: "80.00",
        total_amount: "80.00",
        currency: "GBP",
        paid_at: null,
        items: [
          {
            description: "Consultation",
            quantity: 1,
            unit_amount: "80.00",
            total_amount: "80.00",
          },
        ],
        created_at: "2026-08-19T09:00:00Z",
        updated_at: "2026-08-19T09:00:00Z",
      }).total_amount,
      "80.00",
    );
  });

  it("rejects a non-enumerated client payment state", () => {
    assert.throws(() => paymentSchema.parse({ status: "PAID_ENOUGH" }));
  });
});
