import { Platform } from "react-native";
import { z } from "zod";

import { apiDelete, apiGet, apiPatch, apiPost, apiPostForm } from "./client";
import { API_BASE_URL } from "./config";

export const serviceSchema = z.object({
  public_id: z.string().uuid(),
  name: z.string(),
  slug: z.string(),
  short_description: z.string(),
  duration_minutes: z.number().int().positive(),
  price_amount: z.string(),
  currency: z.string(),
});
const serviceDetailSchema = serviceSchema.extend({ description: z.string() });
export const caseSchema = z.object({
  public_id: z.string().uuid(),
  status: z.enum(["DRAFT", "INTAKE_COMPLETE", "PHOTOS_COMPLETE", "CANCELLED"]),
  service_name: z.string(),
  duration_minutes: z.number(),
  price_amount: z.string(),
  currency: z.string(),
  timezone_snapshot: z.string(),
  hair_profile_snapshot: z.record(z.string(), z.unknown()),
  questionnaire_version: z.number().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  intake_completed_at: z.string().nullable(),
  photos_completed_at: z.string().nullable(),
});
const optionSchema = z.object({ value: z.string(), label: z.string() });
const questionSchema = z.object({
  key: z.string(),
  section: z.string(),
  prompt: z.string(),
  help_text: z.string(),
  type: z.enum([
    "SHORT_TEXT",
    "LONG_TEXT",
    "SINGLE_CHOICE",
    "MULTI_CHOICE",
    "BOOLEAN",
    "DATE",
  ]),
  required: z.boolean(),
  placeholder: z.string(),
  max_length: z.number().nullable(),
  show_if_question_key: z.string(),
  show_if_value: z.string(),
  options: z.array(optionSchema),
});
const questionnaireSchema = z.object({
  public_id: z.string().uuid(),
  version: z.number(),
  title: z.string(),
  introduction: z.string(),
  questions: z.array(questionSchema),
});
const answersSchema = z.object({
  case_public_id: z.string().uuid(),
  status: caseSchema.shape.status,
  answers: z.record(z.string(), z.unknown()),
});
const consentSchema = z.object({
  required: z.boolean(),
  available: z.boolean(),
  accepted: z.boolean(),
  document_public_id: z.string().uuid().nullable(),
  document_title: z.string(),
  document_version: z.number().nullable(),
});
const photoSchema = z.object({
  public_id: z.string().uuid(),
  category: z.enum([
    "FRONT",
    "TOP",
    "LEFT",
    "RIGHT",
    "BACK",
    "CLOSE_UP",
    "OTHER",
  ]),
  category_label: z.string(),
  width: z.number(),
  height: z.number(),
  byte_size: z.number(),
  created_at: z.string(),
  content_path: z.string().nullable(),
});
const photosOverviewSchema = z.object({
  case_public_id: z.string().uuid(),
  status: caseSchema.shape.status,
  editable: z.boolean(),
  max_photos: z.number(),
  consent: consentSchema,
  photos: z.array(photoSchema),
});
const staffCaseSummarySchema = z.object({
  public_id: z.string().uuid(),
  service_name: z.string(),
  client_name: z.string(),
  client_email: z.string().email(),
  photo_count: z.number(),
  photos_completed_at: z.string(),
});
const staffCaseDetailSchema = z.object({
  public_id: z.string().uuid(),
  status: z.literal("PHOTOS_COMPLETE"),
  service_name: z.string(),
  client: z.object({
    public_id: z.string().uuid(),
    first_name: z.string(),
    last_name: z.string(),
    email: z.string().email(),
    phone: z.string(),
  }),
  timezone_snapshot: z.string(),
  hair_profile_snapshot: z.record(z.string(), z.unknown()),
  intake_completed_at: z.string(),
  photos_completed_at: z.string(),
  updated_at: z.string(),
  answers: z.array(
    z.object({ question: z.string(), section: z.string(), value: z.unknown() }),
  ),
  photo_consent_active: z.boolean(),
  photos: z.array(photoSchema),
});

export type ConsultationService = z.infer<typeof serviceSchema>;
export type ConsultationCase = z.infer<typeof caseSchema>;
export type IntakeQuestion = z.infer<typeof questionSchema>;
export type Questionnaire = z.infer<typeof questionnaireSchema>;
export type IntakeAnswers = z.infer<typeof answersSchema>;
export type ConsultationPhoto = z.infer<typeof photoSchema>;
export type ConsultationPhotoCategory = ConsultationPhoto["category"];
export type ConsultationPhotosOverview = z.infer<typeof photosOverviewSchema>;
export type StaffConsultationCase = z.infer<typeof staffCaseDetailSchema>;

export async function getConsultationServices() {
  return z
    .array(serviceSchema)
    .parse(await apiGet<unknown>("/consultation-services/"));
}
export async function getConsultationService(publicId: string) {
  return serviceDetailSchema.parse(
    await apiGet<unknown>(`/consultation-services/${publicId}/`),
  );
}
export async function getConsultations() {
  return z.array(caseSchema).parse(await apiGet<unknown>("/consultations/"));
}
export async function startConsultation(
  servicePublicId: string,
  timezone: string,
) {
  return caseSchema.parse(
    await apiPost<unknown>("/consultations/", {
      service_public_id: servicePublicId,
      timezone,
    }),
  );
}
export async function getConsultation(publicId: string) {
  return caseSchema.parse(await apiGet<unknown>(`/consultations/${publicId}/`));
}
export async function getQuestionnaire(publicId: string) {
  return questionnaireSchema.parse(
    await apiGet<unknown>(`/consultations/${publicId}/questionnaire/`),
  );
}
export async function getAnswers(publicId: string) {
  return answersSchema.parse(
    await apiGet<unknown>(`/consultations/${publicId}/answers/`),
  );
}
export async function saveAnswers(
  publicId: string,
  answers: { question_key: string; value: unknown }[],
) {
  return answersSchema.parse(
    await apiPatch<unknown>(`/consultations/${publicId}/answers/`, { answers }),
  );
}
export async function completeIntake(publicId: string) {
  return caseSchema.parse(
    await apiPost<unknown>(`/consultations/${publicId}/submit/`, {}),
  );
}

export async function getConsultationPhotos(publicId: string) {
  return photosOverviewSchema.parse(
    await apiGet<unknown>(`/consultations/${publicId}/photos/`),
  );
}

export async function uploadConsultationPhoto(
  publicId: string,
  asset: { uri: string; fileName?: string | null; mimeType?: string | null },
  category: ConsultationPhotoCategory,
) {
  const form = new FormData();
  form.append("category", category);
  if (Platform.OS === "web") {
    const blob = await fetch(asset.uri).then((response) => response.blob());
    form.append("file", blob, asset.fileName || "consultation-photo.jpg");
  } else {
    form.append("file", {
      uri: asset.uri,
      name: asset.fileName || "consultation-photo.jpg",
      type: asset.mimeType || "image/jpeg",
    } as unknown as Blob);
  }
  return photosOverviewSchema.parse(
    await apiPostForm<unknown>(`/consultations/${publicId}/photos/`, form),
  );
}

export async function deleteConsultationPhoto(
  publicId: string,
  photoId: string,
) {
  await apiDelete(`/consultations/${publicId}/photos/${photoId}/`);
}

export async function completeConsultationPhotos(publicId: string) {
  return caseSchema.parse(
    await apiPost<unknown>(`/consultations/${publicId}/photos/submit/`, {}),
  );
}

export function privatePhotoUrl(path: string | null) {
  if (!path) return null;
  const apiOrigin = API_BASE_URL.replace(/\/api\/v1\/?$/, "");
  return `${apiOrigin}${path}`;
}

export async function getStaffConsultations(limit = 50) {
  return z
    .array(staffCaseSummarySchema)
    .parse(await apiGet<unknown>(`/staff/consultations/?limit=${limit}`));
}

export async function getStaffConsultation(publicId: string) {
  return staffCaseDetailSchema.parse(
    await apiGet<unknown>(`/staff/consultations/${publicId}/`),
  );
}
