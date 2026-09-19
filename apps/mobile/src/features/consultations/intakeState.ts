export type IntakeStatus =
  "DRAFT" | "INTAKE_COMPLETE" | "PHOTOS_COMPLETE" | "CANCELLED";

type IntakeQuestionShape = {
  key: string;
  type?: string;
  options?: { value: string }[];
};

export function answeredSectionPayload(
  questions: { key: string }[],
  values: Record<string, unknown>,
) {
  return questions
    .filter((question) => values[question.key] !== undefined)
    .map((question) => ({
      question_key: question.key,
      value: values[question.key] ?? null,
    }));
}

export function normalizeIntakeAnswers(
  questions: IntakeQuestionShape[],
  answers: Record<string, unknown>,
) {
  const result = { ...answers };
  for (const question of questions) {
    const value = answers[question.key];
    if (question.type === "BOOLEAN" && typeof value === "string") {
      if (value.toLowerCase() === "true") result[question.key] = true;
      if (value.toLowerCase() === "false") result[question.key] = false;
    }
    if (
      question.type === "SINGLE_CHOICE" &&
      value &&
      typeof value === "object" &&
      "value" in value &&
      typeof value.value === "string"
    ) {
      result[question.key] = value.value;
    }
  }
  return result;
}

export function lockedIntakePath(status: IntakeStatus, caseId: string) {
  if (status === "DRAFT") return null;
  return status === "CANCELLED" ? "/consult" : `/consult/complete/${caseId}`;
}
