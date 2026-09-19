import { z } from "zod";

export const videoStateSchema = z.object({
  appointment_public_id: z.string().uuid(), service_name: z.string(), participant_role: z.enum(["CLIENT", "EXPERT"]),
  appointment_status: z.string(), session_status: z.enum(["NOT_CREATED", "SCHEDULED", "PROVISIONING", "READY", "ACTIVE", "COMPLETED", "CANCELLED", "FAILED"]),
  starts_at: z.string(), ends_at: z.string(), available_from: z.string(), expires_at: z.string(),
  provider_configured: z.boolean(), can_join: z.boolean(), reason_code: z.string(), message: z.string(),
});

export const joinGrantSchema = z.object({
  session_public_id: z.string().uuid(),
  join_url: z.string().url().refine((url) => url.startsWith("https://"), "A secure video URL is required."),
  expires_at: z.string(),
});

export const videoEventResultSchema = z.object({ event_public_id: z.string().uuid(), event_type: z.string() });

