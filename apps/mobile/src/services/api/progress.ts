import { z } from "zod";

import { apiDelete, apiGet, apiPatch, apiPost, apiPostForm } from "./client";
import { appendAssetToFormData, type MultipartAsset } from "./multipart";

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
  created_at: z.string(),
  content_path: z.string().nullable(),
});
export const progressSchema = z.object({
  public_id: z.string().uuid(),
  case_public_id: z.string().uuid(),
  service_name: z.string(),
  client_name: z.string(),
  sequence: z.number(),
  status: z.enum(["DRAFT", "SUBMITTED", "REVIEWED"]),
  summary: z.string(),
  wins: z.string(),
  challenges: z.string(),
  routine_adherence: z.number().nullable(),
  questions_for_tk: z.string(),
  submitted_at: z.string().nullable(),
  expert_feedback: z.string(),
  feedback_published_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  photos: z.array(photoSchema),
  baseline_photos: z.array(photoSchema),
});
const consentSchema = z.object({
  required: z.boolean(),
  available: z.boolean(),
  accepted: z.boolean(),
  document_public_id: z.string().uuid().nullable(),
  document_title: z.string(),
  document_version: z.number().nullable(),
});
const photosSchema = z.object({
  check_in_public_id: z.string().uuid(),
  editable: z.boolean(),
  max_photos: z.number(),
  consent: consentSchema,
  photos: z.array(photoSchema),
});

export type ProgressCheckIn = z.infer<typeof progressSchema>;
export type ProgressCategory = z.infer<typeof photoSchema>["category"];
export type ProgressInput = {
  summary: string;
  wins: string;
  challenges: string;
  routine_adherence: number | null;
  questions_for_tk: string;
};

export async function getProgress() {
  return z.array(progressSchema).parse(await apiGet<unknown>("/progress/"));
}
export async function createProgress(caseId: string) {
  return progressSchema.parse(
    await apiPost<unknown>(`/consultations/${caseId}/progress/`, {}),
  );
}
export async function getProgressCheckIn(publicId: string) {
  return progressSchema.parse(await apiGet<unknown>(`/progress/${publicId}/`));
}
export async function updateProgress(publicId: string, input: ProgressInput) {
  return progressSchema.parse(
    await apiPatch<unknown>(`/progress/${publicId}/`, input),
  );
}
export async function submitProgress(publicId: string) {
  return progressSchema.parse(
    await apiPost<unknown>(`/progress/${publicId}/submit/`, {}),
  );
}
export async function getProgressPhotos(publicId: string) {
  return photosSchema.parse(
    await apiGet<unknown>(`/progress/${publicId}/photos/`),
  );
}
export async function uploadProgressPhoto(
  publicId: string,
  asset: MultipartAsset,
  category: ProgressCategory,
) {
  const form = new FormData();
  form.append("category", category);
  await appendAssetToFormData(form, "file", asset, "progress-photo.jpg");
  return photosSchema.parse(
    await apiPostForm<unknown>(`/progress/${publicId}/photos/`, form),
  );
}
export async function deleteProgressPhoto(publicId: string, photoId: string) {
  await apiDelete(`/progress/${publicId}/photos/${photoId}/`);
}
export async function getStaffProgress() {
  return z
    .array(progressSchema)
    .parse(await apiGet<unknown>("/staff/progress/"));
}
export async function getStaffProgressCheckIn(publicId: string) {
  return progressSchema.parse(
    await apiGet<unknown>(`/staff/progress/${publicId}/`),
  );
}
export async function saveProgressFeedback(
  publicId: string,
  expert_feedback: string,
) {
  return progressSchema.parse(
    await apiPatch<unknown>(`/staff/progress/${publicId}/`, {
      expert_feedback,
    }),
  );
}
export async function publishProgressFeedback(publicId: string) {
  return progressSchema.parse(
    await apiPost<unknown>(`/staff/progress/${publicId}/publish/`, {}),
  );
}
