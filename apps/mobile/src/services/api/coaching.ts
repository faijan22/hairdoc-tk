import { z } from "zod";

import { apiGet, apiPatch, apiPost } from "./client";

const sectionSchema = z.object({
  public_id: z.string().uuid(),
  title: z.string(),
  body: z.string(),
  display_order: z.number(),
});
const recommendationSchema = z.object({
  public_id: z.string().uuid(),
  category: z.enum([
    "ROUTINE",
    "PRODUCT",
    "LIFESTYLE",
    "FOLLOW_UP",
    "RESOURCE",
  ]),
  category_label: z.string(),
  title: z.string(),
  guidance: z.string(),
  external_url: z.string(),
  display_order: z.number(),
});
export const coachingPlanSchema = z.object({
  public_id: z.string().uuid(),
  case_public_id: z.string().uuid(),
  client_name: z.string(),
  service_name: z.string(),
  version: z.number(),
  title: z.string(),
  summary: z.string(),
  status: z.enum(["DRAFT", "PUBLISHED"]),
  published_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  sections: z.array(sectionSchema),
  recommendations: z.array(recommendationSchema),
});

export type CoachingPlan = z.infer<typeof coachingPlanSchema>;
export type CoachingCategory =
  CoachingPlan["recommendations"][number]["category"];
export type CoachingPlanInput = {
  title: string;
  summary: string;
  sections: { title: string; body: string }[];
  recommendations: {
    category: CoachingCategory;
    title: string;
    guidance: string;
    external_url: string;
  }[];
};

export async function getPlans() {
  return z.array(coachingPlanSchema).parse(await apiGet<unknown>("/plans/"));
}
export async function getPlan(publicId: string) {
  return coachingPlanSchema.parse(await apiGet<unknown>(`/plans/${publicId}/`));
}
export async function getStaffCasePlans(caseId: string) {
  return z
    .array(coachingPlanSchema)
    .parse(await apiGet<unknown>(`/staff/consultations/${caseId}/plans/`));
}
export async function getStaffPlan(publicId: string) {
  return coachingPlanSchema.parse(
    await apiGet<unknown>(`/staff/plans/${publicId}/`),
  );
}
export async function createStaffPlan(caseId: string) {
  return coachingPlanSchema.parse(
    await apiPost<unknown>(`/staff/consultations/${caseId}/plans/`, {
      title: "Your care plan",
      summary: "",
    }),
  );
}
export async function updateStaffPlan(
  publicId: string,
  input: CoachingPlanInput,
) {
  return coachingPlanSchema.parse(
    await apiPatch<unknown>(`/staff/plans/${publicId}/`, input),
  );
}
export async function publishStaffPlan(publicId: string) {
  return coachingPlanSchema.parse(
    await apiPost<unknown>(`/staff/plans/${publicId}/publish/`, {}),
  );
}
