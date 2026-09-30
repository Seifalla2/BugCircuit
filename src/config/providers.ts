import type { Provider } from "../core/types.js";
import { OpenAICompatibleProvider } from "../providers/openai-compatible.js";

function addOpenAICompatible(
  providers: Provider[],
  id: string,
  baseUrl: string,
  model: string,
  apiKey?: string,
): void {
  if (!apiKey) return;
  providers.push(new OpenAICompatibleProvider({ id, baseUrl, model, apiKey }));
}

export function loadProvidersFromEnv(): Provider[] {
  const providers: Provider[] = [];

  // Priority 1: OpenRouter free-model router.
  addOpenAICompatible(
    providers,
    "openrouter-free",
    "https://openrouter.ai/api/v1",
    process.env.CT_AI_OPENROUTER_MODEL?.trim() || "openrouter/free",
    process.env.OPENROUTER_API_KEY?.trim(),
  );

  // Priority 2: Groq's OpenAI-compatible API.
  addOpenAICompatible(
    providers,
    "groq-free",
    "https://api.groq.com/openai/v1",
    process.env.CT_AI_GROQ_MODEL?.trim() || "openai/gpt-oss-120b",
    process.env.GROQ_API_KEY?.trim(),
  );

  // Priority 3: Gemini OpenAI compatibility endpoint.
  addOpenAICompatible(
    providers,
    "gemini-free",
    "https://generativelanguage.googleapis.com/v1beta/openai",
    process.env.CT_AI_GEMINI_MODEL?.trim() || "gemini-2.5-flash",
    process.env.GEMINI_API_KEY?.trim(),
  );

  // Optional self-hosted OmniRoute gateway.
  const omniBase = process.env.CT_AI_OMNIROUTE_BASE_URL?.trim();
  if (omniBase) {
    providers.push(new OpenAICompatibleProvider({
      id: "omniroute",
      baseUrl: omniBase,
      model: process.env.CT_AI_OMNIROUTE_MODEL?.trim() || "auto",
      apiKey: process.env.CT_AI_OMNIROUTE_API_KEY?.trim() || undefined,
    }));
  }

  // Optional generic/OpenAI-compatible endpoint. Disabled unless configured.
  const genericBase = process.env.CT_AI_OPENAI_BASE_URL?.trim();
  const genericModel = process.env.CT_AI_OPENAI_MODEL?.trim();
  if (genericBase && genericModel) {
    providers.push(new OpenAICompatibleProvider({
      id: process.env.CT_AI_OPENAI_PROVIDER_ID?.trim() || "openai-compatible",
      baseUrl: genericBase,
      model: genericModel,
      apiKey: process.env.CT_AI_OPENAI_API_KEY?.trim() || undefined,
    }));
  }

  return providers;
}
