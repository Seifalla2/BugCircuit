import assert from "node:assert/strict";
import test from "node:test";
import { OpenAICompatibleProvider, ProviderRateLimitError } from "../src/providers/openai-compatible.js";

test("normalizes an OpenAI-compatible completion", async () => {
  const provider = new OpenAICompatibleProvider({
    id: "test", baseUrl: "https://example.invalid/v1", model: "test-model",
    fetchImpl: async () => new Response(JSON.stringify({
      model: "resolved-model", choices: [{ message: { content: "hello" } }],
    }), { status: 200, headers: { "content-type": "application/json" } }),
  });
  const result = await provider.complete({ messages: [{ role: "user", content: "hi" }] });
  assert.deepEqual(result, { provider: "test", model: "resolved-model", content: "hello" });
});

test("exposes HTTP 429 as a quota error with retry-after", async () => {
  const provider = new OpenAICompatibleProvider({
    id: "limited", baseUrl: "https://example.invalid/v1", model: "test-model",
    fetchImpl: async () => new Response("", { status: 429, headers: { "retry-after": "30" } }),
  });
  await assert.rejects(provider.complete({ messages: [] }),
    (error: unknown) => error instanceof ProviderRateLimitError && error.retryAfterMs === 30_000);
});
