import { z } from "zod";

import { getApiFieldErrors } from "./errors";

type SetError = (field: string, message: string) => void;

export function applyZodErrors(error: z.ZodError, setError: SetError): void {
  for (const issue of error.issues) {
    const field = String(issue.path[0] || "root");
    setError(field, issue.message);
  }
}

export function applyApiFieldErrors(error: unknown, setError: SetError): void {
  for (const [field, messages] of Object.entries(getApiFieldErrors(error))) {
    if (messages[0]) setError(field, messages[0]);
  }
}
