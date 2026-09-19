import assert from "node:assert/strict";
import test from "node:test";

import {
  answeredSectionPayload,
  lockedIntakePath,
  normalizeIntakeAnswers,
} from "./intakeState.ts";

test("a section saves every answered control including an explicit No", () => {
  const questions = [{ key: "notes" }, { key: "first_extensions" }];
  assert.deepEqual(
    answeredSectionPayload(questions, {
      notes: "Saved earlier",
      first_extensions: false,
    }),
    [
      { question_key: "notes", value: "Saved earlier" },
      { question_key: "first_extensions", value: false },
    ],
  );
});

test("unanswered controls are omitted instead of erasing saved answers", () => {
  assert.deepEqual(
    answeredSectionPayload(
      [{ key: "notes" }, { key: "first_extensions" }],
      { notes: "Kept" },
    ),
    [{ question_key: "notes", value: "Kept" }],
  );
});

test("resume normalizes legacy boolean and selected-option values", () => {
  assert.deepEqual(
    normalizeIntakeAnswers(
      [
        { key: "first_extensions", type: "BOOLEAN" },
        { key: "routine", type: "SINGLE_CHOICE" },
      ],
      {
        first_extensions: "false",
        routine: { value: "simple", label: "Simple" },
      },
    ),
    { first_extensions: false, routine: "simple" },
  );
});

test("completed intake routes cannot reopen the editable form", () => {
  assert.equal(lockedIntakePath("DRAFT", "case-1"), null);
  assert.equal(
    lockedIntakePath("INTAKE_COMPLETE", "case-1"),
    "/consult/complete/case-1",
  );
  assert.equal(lockedIntakePath("CANCELLED", "case-1"), "/consult");
});
