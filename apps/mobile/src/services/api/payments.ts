import { apiGet, apiPost } from "./client";
import {
  checkoutSchema,
  orderSchema,
  paymentSchema,
  staffPaymentSchema,
} from "./paymentSchemas";

export { orderSchema, paymentSchema } from "./paymentSchemas";
export type { Payment, StaffPayment } from "./paymentSchemas";

export async function createOrder(appointmentId: string) {
  return orderSchema.parse(
    await apiPost<unknown>("/orders/", {
      appointment_public_id: appointmentId,
    }),
  );
}
export async function createCheckout(orderId: string) {
  return checkoutSchema.parse(
    await apiPost<unknown>(`/orders/${orderId}/checkout/`),
  );
}
export async function getPayments() {
  return paymentSchema.array().parse(await apiGet<unknown>("/payments/"));
}
export async function getPayment(paymentId: string) {
  return paymentSchema.parse(await apiGet<unknown>(`/payments/${paymentId}/`));
}
export async function refreshPayment(paymentId: string) {
  return paymentSchema.parse(
    await apiPost<unknown>(`/payments/${paymentId}/refresh/`, {}),
  );
}
export async function getStaffPayments() {
  return staffPaymentSchema.array().parse(await apiGet<unknown>("/staff/payments/"));
}
export async function getStaffPayment(paymentId: string) {
  return staffPaymentSchema.parse(await apiGet<unknown>(`/staff/payments/${paymentId}/`));
}
