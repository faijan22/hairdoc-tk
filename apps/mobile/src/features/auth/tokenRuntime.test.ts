import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  configureRefreshHandler,
  getAccessToken,
  refreshAccessToken,
  setAccessToken,
} from "./tokenRuntime.ts";

describe("token runtime", () => {
  it("keeps access tokens in memory and coalesces refreshes", async () => {
    let calls = 0;
    setAccessToken("initial");
    configureRefreshHandler(async () => {
      calls += 1;
      await Promise.resolve();
      setAccessToken("rotated");
      return "rotated";
    });

    const results = await Promise.all([refreshAccessToken(), refreshAccessToken()]);
    assert.deepEqual(results, ["rotated", "rotated"]);
    assert.equal(calls, 1);
    assert.equal(getAccessToken(), "rotated");
  });
});
