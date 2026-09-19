import { z } from "zod";

const refundSchema = z.object({
  public_id: z.string().uuid(),
  amount: z.string(),
  currency: z.string(),
  status: z.enum(["REQUESTED", "PROCESSING", "SUCCEEDED", "FAILED"]),
  status_label: z.string(),
  reason: z.string(),
  created_at: z.string(),
});
const orderItemSchema = z.object({
  description: z.string(),
  quantity: z.number().int(),
  unit_amount: z.string(),
  total_amount: z.string(),
});
export const orderSchema = z.object({
  public_id: z.string().uuid(),
  appointment_public_id: z.string().uuid(),
  consultation_public_id: z.string().uuid(),
  service_name: z.string(),
  appointment_starts_at: z.string(),
  status: z.enum([
    "PENDING",
    "PAID",
    "CANCELLED",
    "EXPIRED",
    "REFUND_PENDING",
    "PARTIALLY_REFUNDED", "REFUNDED",
  ]),
  status_label: z.string(),
  payment_public_id: z.string().uuid().nullable(),
  payment_status: z.string().nullable(),
  subtotal_amount: z.string(),
  total_amount: z.string(),
  currency: z.string(),
  paid_at: z.string().nullable(),
  items: z.array(orderItemSchema),
  created_at: z.string(),
  updated_at: z.string(),
});
export const paymentSchema = z.object({
  public_id: z.string().uuid(),
  order_public_id: z.string().uuid(),
  appointment_public_id: z.string().uuid(),
  consultation_public_id: z.string().uuid(),
  service_name: z.string(),
  appointment_starts_at: z.string(),
  provider: z.string(),
  status: z.enum([
    "CREATED",
    "PROCESSING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
    "REFUND_PENDING",
    "PARTIALLY_REFUNDED",
    "REFUNDED",
  ]),
  status_label: z.string(),
  amount: z.string(),
  currency: z.string(),
  receipt_number: z.string(),
  paid_at: z.string().nullable(),
  failure_message: z.string(),
  refunds: z.array(refundSchema),
  created_at: z.string(),
  updated_at: z.string(),
});
export const staffPaymentSchema = paymentSchema.extend({
  client_name: z.string(),
  client_email: z.string().email(),
});
export const checkoutSchema = z.object({
  payment: paymentSchema,
  checkout_url: z.string().url(),
  expires_at: z.string(),
});

export type Payment = z.infer<typeof paymentSchema>;
export type StaffPayment = z.infer<typeof staffPaymentSchema>;
