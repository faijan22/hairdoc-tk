import { z } from "zod";

import { appointmentSchema } from "./bookings";
import { apiGet } from "./client";
import { caseSchema, serviceSchema } from "./consultations";
import { contentItemSchema } from "./content";

const homeSchema = z.object({
  services: z.array(serviceSchema),
  active_consultation: caseSchema.nullable(),
  next_appointment: appointmentSchema.nullable(),
  content: z.array(contentItemSchema),
});

export type HomeData = z.infer<typeof homeSchema>;

export async function getHome(): Promise<HomeData> {
  return homeSchema.parse(await apiGet<unknown>("/home/"));
}
