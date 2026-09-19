import { apiGet, apiPost } from "./client";
import { joinGrantSchema, videoEventResultSchema, videoStateSchema } from "./videoSchemas";

export type VideoEventType = "JOINED" | "LEFT" | "RECONNECTED" | "PERMISSION_DENIED";

export async function getVideoState(appointmentId: string) {
  return videoStateSchema.parse(await apiGet<unknown>(`/appointments/${appointmentId}/video/`));
}

export async function joinVideo(appointmentId: string) {
  return joinGrantSchema.parse(await apiPost<unknown>(`/appointments/${appointmentId}/video/join/`));
}

export async function reportVideoEvent(appointmentId: string, eventType: VideoEventType) {
  const clientEventId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return videoEventResultSchema.parse(await apiPost<unknown>(`/appointments/${appointmentId}/video/events/`, {
    event_type: eventType,
    client_event_id: clientEventId,
  }));
}

export async function completeVideo(appointmentId: string) {
  return videoStateSchema.parse(await apiPost<unknown>(`/appointments/${appointmentId}/video/complete/`));
}
