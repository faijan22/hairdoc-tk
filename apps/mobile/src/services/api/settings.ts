import { z } from "zod";

import { apiGet, apiPatch, apiPost } from "./client";
import { API_BASE_URL } from "./config";

export const hairTextures = ["STRAIGHT", "WAVY", "CURLY", "COILY", "UNSURE", "PREFER_NOT_TO_SAY"] as const;
export const scalpTypes = ["BALANCED", "DRY", "OILY", "SENSITIVE", "UNSURE"] as const;
export const legalTypes = ["TERMS", "PRIVACY", "CONSULTATION_DISCLAIMER", "PHOTO_DATA_CONSENT"] as const;

const hairProfileSchema = z.object({
  hair_texture: z.enum(hairTextures).or(z.literal("")),
  scalp_type: z.enum(scalpTypes).or(z.literal("")),
  concerns: z.string(),
  goals: z.string(),
  current_routine: z.string(),
  updated_at: z.string(),
});

const preferencesSchema = z.object({
  timezone: z.string(),
  email_enabled: z.boolean(),
  push_enabled: z.boolean(),
  appointment_reminders: z.boolean(),
  message_notifications: z.boolean(),
  coaching_updates: z.boolean(),
  updated_at: z.string(),
});

const legalDocumentSchema = z.object({
  public_id: z.string().uuid(),
  type: z.enum(legalTypes),
  type_label: z.string(),
  version: z.number().int().positive(),
  title: z.string(),
  body: z.string(),
  attachment_name: z.string(),
  attachment_path: z.string().nullable(),
  published_at: z.string(),
});

const consentSchema = z.object({
  document: legalDocumentSchema,
  accepted: z.boolean(),
  accepted_at: z.string(),
  withdrawn_at: z.string().nullable(),
});

export type HairProfile = z.infer<typeof hairProfileSchema>;
export type NotificationPreferences = z.infer<typeof preferencesSchema>;
export type LegalType = (typeof legalTypes)[number];
export type LegalDocument = z.infer<typeof legalDocumentSchema>;
export type UserConsent = z.infer<typeof consentSchema>;

export async function getHairProfile() {
  return hairProfileSchema.parse(await apiGet<unknown>("/me/hair-profile/"));
}

export async function updateHairProfile(input: Omit<HairProfile, "updated_at">) {
  return hairProfileSchema.parse(await apiPatch<unknown>("/me/hair-profile/", input));
}

export async function getNotificationPreferences() {
  return preferencesSchema.parse(await apiGet<unknown>("/me/notification-preferences/"));
}

export async function updateNotificationPreferences(input: Partial<Omit<NotificationPreferences, "updated_at">>) {
  return preferencesSchema.parse(await apiPatch<unknown>("/me/notification-preferences/", input));
}

export async function getLegalDocument(type: LegalType) {
  return legalDocumentSchema.parse(await apiGet<unknown>(`/legal/${type}/current/`));
}

export async function getConsents() {
  return z.array(consentSchema).parse(await apiGet<unknown>("/me/consents/"));
}

export async function updateConsent(documentPublicId: string, accepted: boolean) {
  return consentSchema.parse(
    await apiPost<unknown>("/me/consents/", { document_public_id: documentPublicId, accepted }),
  );
}

export function legalFileUrl(path: string) {
  const apiOrigin = API_BASE_URL.replace(/\/api\/v1\/?$/, "");
  return `${apiOrigin}${path}`;
}
