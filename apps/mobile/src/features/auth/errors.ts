import { z } from "zod";

import { ApiError } from "@/services/api/client";

type FieldErrors = Record<string, string[]>;

export function getApiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof z.ZodError) return "The app and local server are out of sync. Stop and restart npm run dev.";
  if (error instanceof Error) return error.message;
  return "Something went wrong. Please try again.";
}

export function getApiFieldErrors(error: unknown): FieldErrors {
  if (!(error instanceof ApiError) || !error.details || typeof error.details !== "object") return {};
  const details = error.details as Record<string, unknown>;
  const result: FieldErrors = {};
  for (const [field, messages] of Object.entries(details)) {
    if (Array.isArray(messages)) result[field] = messages.map(String);
  }
  return result;
}
