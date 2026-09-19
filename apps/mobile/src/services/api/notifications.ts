import { z } from "zod";

import { apiDelete, apiGet, apiPost } from "./client";

export const notificationKinds = [
  "NEW_MESSAGE",
  "CONSULTATION_SUBMITTED",
  "APPOINTMENT_CONFIRMED",
  "APPOINTMENT_RESCHEDULED",
  "APPOINTMENT_CANCELLED",
  "APPOINTMENT_REMINDER_24H",
  "APPOINTMENT_REMINDER_1H",
  "COACHING_PLAN_PUBLISHED",
  "PROGRESS_SUBMITTED",
  "PROGRESS_FEEDBACK_PUBLISHED",
] as const;

const notificationSchema = z.object({
  public_id: z.string().uuid(),
  kind: z.enum(notificationKinds),
  title: z.string(),
  body: z.string(),
  route: z.string(),
  conversation_public_id: z.string().uuid().nullable(),
  read_at: z.string().nullable(),
  created_at: z.string(),
});

const notificationPageSchema = z.object({
  unread_count: z.number().int().nonnegative(),
  results: z.array(notificationSchema),
});

const pushDeviceSchema = z.object({
  public_id: z.string().uuid(),
  expo_token: z.string(),
  platform: z.enum(["IOS", "ANDROID"]),
  device_id: z.string(),
  active: z.boolean(),
  last_seen_at: z.string(),
});

export type CareNotification = z.infer<typeof notificationSchema>;
export type NotificationPage = z.infer<typeof notificationPageSchema>;

export function parseRealtimeNotification(value: unknown) {
  return notificationSchema.parse(value);
}

export function parseRealtimeNotificationReads(value: unknown) {
  return z.object({
    notification_ids: z.array(z.string().uuid()),
    read_at: z.string(),
    unread_count: z.number().int().nonnegative(),
  }).parse(value);
}

export async function getNotifications() {
  return notificationPageSchema.parse(
    await apiGet<unknown>("/notifications/"),
  );
}

export async function markNotificationRead(id: string) {
  return notificationSchema.parse(
    await apiPost<unknown>(`/notifications/${id}/read/`),
  );
}

export async function markAllNotificationsRead() {
  return z
    .object({ unread_count: z.literal(0) })
    .parse(await apiPost<unknown>("/notifications/read-all/"));
}

export async function getPushDevices() {
  return pushDeviceSchema
    .array()
    .parse(await apiGet<unknown>("/push-devices/"));
}

export async function registerPushDevice(input: {
  expo_token: string;
  platform: "IOS" | "ANDROID";
  device_id: string;
}) {
  return pushDeviceSchema.parse(
    await apiPost<unknown>("/push-devices/", input),
  );
}

export async function removePushDevice(id: string) {
  return apiDelete(`/push-devices/${id}/`);
}
