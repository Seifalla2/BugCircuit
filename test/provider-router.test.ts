import assert from "node:assert/strict";
import test from "node:test";
import { ProviderRouter } from "../src/core/provider-router.js";
import type { Provider } from "../src/core/types.js";

test("router falls back after a provider failure", async () => {
  const broken: Provider = {
    id: "broken",
    async isAvailable() { return true; },
    async complete() { throw new Error("quota"); },
  };
  const healthy: Provider = {
    id: "healthy",
    async isAvailable() { return true; },
    async complete() {
      return { provider: "healthy", model: "test", content: "ok" };
    },
  };

  const result = await new ProviderRouter([broken, healthy]).complete({ messages: [] });
  assert.equal(result.provider, "healthy");
});
