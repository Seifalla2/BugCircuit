import assert from "node:assert/strict";
import test from "node:test";
import { checkOpenAICompatibleGateway } from "../src/providers/gateway-health.js";

test("reads model catalog from an OpenAI-compatible gateway", async () => {
  const result = await checkOpenAICompatibleGateway(
    "http://localhost:20128/v1/",
    "secret",
    async (input, init) => {
      assert.equal(String(input), "http://localhost:20128/v1/models");
      assert.equal((init?.headers as Record<string,string>).authorization, "Bearer secret");
      return new Response(JSON.stringify({ data: [{ id: "auto" }, { id: "provider/model" }] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    },
  );
  assert.deepEqual(result, { ok: true, status: 200, models: ["auto", "provider/model"] });
});
