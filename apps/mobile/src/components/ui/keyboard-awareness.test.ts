import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

function filesUnder(root: string): string[] {
  return readdirSync(root, { withFileTypes: true }).flatMap((entry) => {
    const path = join(root, entry.name);
    return entry.isDirectory() ? filesUnder(path) : [path];
  });
}

test("editable mobile screens use a keyboard-aware container", () => {
  const featureRoot = join(process.cwd(), "src", "features");
  const offenders = filesUnder(featureRoot)
    .filter((path) => path.endsWith(".tsx"))
    .filter((path) => {
      const source = readFileSync(path, "utf8");
      const hasInput =
        source.includes("<TextField") || source.includes("<TextInput");
      const hasAwareContainer =
        source.includes("<Screen") ||
        source.includes("<AuthShell") ||
        source.includes("<KeyboardAvoidingView");
      return hasInput && !hasAwareContainer;
    });
  assert.deepEqual(offenders, []);

  const screen = readFileSync(
    join(process.cwd(), "src", "components", "ui", "Screen.tsx"),
    "utf8",
  );
  assert.match(screen, /keyboardAware = true/);
  assert.match(screen, /automaticallyAdjustKeyboardInsets/);

  const config = JSON.parse(
    readFileSync(join(process.cwd(), "app.json"), "utf8"),
  );
  assert.equal(config.expo.android.softwareKeyboardLayoutMode, "resize");
});
