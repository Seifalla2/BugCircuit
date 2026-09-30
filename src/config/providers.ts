import type { Provider } from "../core/types.js";
import { OpenAICompatibleProvider } from "../providers/openai-compatible.js";

export function loadProvidersFromEnv(): Provider[] {
  const baseUrl = process.env.CT_AI_OMNIROUTE_BASE_URL?.trim()
    || process.env.CT_AI_OPENAI_BASE_URL?.trim();
  const model = process.env.CT_AI_OMNIROUTE_MODEL?.trim()
    || process.env.CT_AI_OPENAI_MODEL?.trim()
    || "auto";
  if (!baseUrl) return [];

  return [new OpenAICompatibleProvider({
    id: process.env.CT_AI_OPENAI_PROVIDER_ID?.trim() || "omniroute",
    baseUrl,
    model,
    apiKey: process.env.CT_AI_OMNIROUTE_API_KEY?.trim()
      || process.env.CT_AI_OPENAI_API_KEY?.trim()
      || undefined,
  })];
}
