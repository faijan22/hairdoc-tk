import { z } from "zod";

import { apiDelete, apiGet, apiPatch, apiPost } from "./client";

export const appointmentStatuses = ["PAYMENT_PENDING", "CONFIRMED", "CANCELLED", "EXPIRED", "COMPLETED", "NO_SHOW"] as const;
export const appointmentSchema = z.object({
  public_id: z.string().uuid(), consultation_public_id: z.string().uuid(), service_name: z.string(),
  client_name: z.string(), client_email: z.string().email(), expert_name: z.string(), starts_at: z.string(), ends_at: z.string(),
  status: z.enum(appointmentStatuses), status_label: z.string(), client_timezone: z.string(), expert_timezone: z.string(),
  reservation_expires_at: z.string().nullable(), cancelled_at: z.string().nullable(), cancel_reason: z.string(),
  created_at: z.string(), updated_at: z.string(),
});
const slotSchema = z.object({
  starts_at: z.string(), ends_at: z.string(), local_date: z.string(), local_start: z.string(), local_end: z.string(),
});
const slotsSchema = z.object({
  consultation_public_id: z.string().uuid(), service_name: z.string(), duration_minutes: z.number(),
  timezone: z.string(), expert_timezone: z.string(), expert_name: z.string(), slots: z.array(slotSchema),
});
const weeklyRuleSchema = z.object({
  public_id: z.string().uuid(), weekday: z.number().int().min(0).max(6), local_start: z.string(), local_end: z.string(),
  timezone: z.string(), effective_from: z.string().nullable(), effective_until: z.string().nullable(), is_active: z.boolean(),
});
const weeklyAvailabilitySchema = z.object({ timezone: z.string(), rules: z.array(weeklyRuleSchema) });
const exceptionSchema = z.object({
  public_id: z.string().uuid(), date: z.string(), kind: z.enum(["BLOCKED", "EXTRA"]),
  local_start: z.string().nullable(), local_end: z.string().nullable(), timezone: z.string(), note: z.string(),
});

export type Appointment = z.infer<typeof appointmentSchema>;
export type AvailableSlot = z.infer<typeof slotSchema>;
export type WeeklyAvailability = z.infer<typeof weeklyAvailabilitySchema>;
export type AvailabilityException = z.infer<typeof exceptionSchema>;

export async function getAvailableSlots(consultationId: string, dateFrom: string, dateTo: string, timezone: string) {
  const query = `consultation=${encodeURIComponent(consultationId)}&date_from=${dateFrom}&date_to=${dateTo}&timezone=${encodeURIComponent(timezone)}`;
  return slotsSchema.parse(await apiGet<unknown>(`/availability/slots/?${query}`, 10_000));
}

export async function getAppointments() {
  return z.array(appointmentSchema).parse(await apiGet<unknown>("/appointments/"));
}

export async function getAppointment(publicId: string) {
  return appointmentSchema.parse(await apiGet<unknown>(`/appointments/${publicId}/`));
}

export async function createAppointment(consultationId: string, startsAt: string, timezone: string) {
  return appointmentSchema.parse(await apiPost<unknown>("/appointments/", {
    consultation_public_id: consultationId, starts_at: startsAt, timezone,
  }));
}

export async function rescheduleAppointment(publicId: string, startsAt: string, timezone: string) {
  return appointmentSchema.parse(await apiPost<unknown>(`/appointments/${publicId}/reschedule/`, {
    starts_at: startsAt, timezone,
  }));
}

export async function cancelAppointment(publicId: string, reason: string) {
  return appointmentSchema.parse(await apiPost<unknown>(`/appointments/${publicId}/cancel/`, { reason }));
}

export async function getStaffWeeklyAvailability() {
  return weeklyAvailabilitySchema.parse(await apiGet<unknown>("/staff/availability/weekly/"));
}

export async function updateStaffWeeklyAvailability(
  timezone: string,
  rules: { weekday: number; local_start: string; local_end: string; is_active: boolean }[],
) {
  return weeklyAvailabilitySchema.parse(await apiPatch<unknown>("/staff/availability/weekly/", { timezone, rules }));
}

export async function getStaffAvailabilityExceptions() {
  return z.array(exceptionSchema).parse(await apiGet<unknown>("/staff/availability/exceptions/"));
}

export async function createStaffAvailabilityException(input: {
  date: string; kind: "BLOCKED" | "EXTRA"; local_start: string | null; local_end: string | null;
  timezone: string; note: string;
}) {
  return exceptionSchema.parse(await apiPost<unknown>("/staff/availability/exceptions/", input));
}

export async function deleteStaffAvailabilityException(publicId: string) {
  await apiDelete(`/staff/availability/exceptions/${publicId}/`);
}

export async function getStaffAppointments() {
  return z.array(appointmentSchema).parse(await apiGet<unknown>("/staff/appointments/"));
}
