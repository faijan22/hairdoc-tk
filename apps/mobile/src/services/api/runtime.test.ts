import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { resolveApiBaseUrl } from "./runtime.ts";

describe("resolveApiBaseUrl", () => {
  it("prefers and normalizes an explicit URL", () => {
    assert.equal(
      resolveApiBaseUrl({ explicitUrl: " http://10.0.0.9:8000/api/v1/ " }),
      "http://10.0.0.9:8000/api/v1",
    );
  });

  it("uses the Metro host for a physical device", () => {
    assert.equal(
      resolveApiBaseUrl({ hostUri: "192.168.5.105:8081" }),
      "http://192.168.5.105:8000/api/v1",
    );
  });

  it("uses the Expo tunnel API bridge on native", () => {
    assert.equal(
      resolveApiBaseUrl({
        configuredUrl: "http://192.168.5.102:8000/api/v1",
        hostUri: "example-user-8081.exp.direct",
      }),
      "https://example-user-8081.exp.direct/__hairdoc_api/api/v1",
    );
  });

  it("uses the tunnel bridge instead of a stale private explicit URL", () => {
    assert.equal(
      resolveApiBaseUrl({
        explicitUrl: "http://192.168.5.102:8000/api/v1",
        hostUri: "example-user-8081.exp.direct",
      }),
      "https://example-user-8081.exp.direct/__hairdoc_api/api/v1",
    );
  });

  it("preserves an explicit hosted API while using a tunnel", () => {
    assert.equal(
      resolveApiBaseUrl({
        explicitUrl: "https://api.hairdoctk.example/api/v1",
        hostUri: "example-user-8081.exp.direct",
      }),
      "https://api.hairdoctk.example/api/v1",
    );
  });

  it("keeps local web and its configured backend on the same site", () => {
    assert.equal(
      resolveApiBaseUrl({
        configuredUrl: "http://192.168.5.102:8000/api/v1",
        hostUri: "example-user-8081.exp.direct",
        browserHostname: "localhost",
        isWeb: true,
      }),
      "http://localhost:8000/api/v1",
    );
  });

  it("uses the same-origin bridge when web is opened through the Expo tunnel", () => {
    assert.equal(
      resolveApiBaseUrl({
        configuredUrl: "http://192.168.5.102:8000/api/v1",
        hostUri: "example-user-8081.exp.direct",
        browserHostname: "example-user-8081.exp.direct",
        isWeb: true,
      }),
      "https://example-user-8081.exp.direct/__hairdoc_api/api/v1",
    );
  });
});
