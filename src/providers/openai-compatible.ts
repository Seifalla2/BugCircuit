import type { ModelRequest, ModelResponse, Provider } from "../core/types.js";

export class ProviderRateLimitError extends Error {
  constructor(
    message: string,
    public readonly retryAfterMs?: number,
  ) {
    super(message);
    this.name = "ProviderRateLimitError";
  }
}

interface OpenAICompatibleProviderOptions {
  id: string;
  baseUrl: string;
  apiKey?: string;
  model: string;
  fetchImpl?: typeof fetch;
}

export class OpenAICompatibleProvider implements Provider {
  readonly id: string;
  private readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly model: string;
  private readonly fetchImpl: typeof fetch;

  constructor(options: OpenAICompatibleProviderOptions) {
    this.id = options.id;
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.apiKey = options.apiKey;
    this.model = options.model;
    this.fetchImpl = options.fetchImpl ?? fetch;
  }

  async isAvailable(): Promise<boolean> {
    return Boolean(this.baseUrl && this.model);
  }

  async complete(request: ModelRequest): Promise<ModelResponse> {
    const response = await this.fetchImpl(`${this.baseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...(this.apiKey ? { authorization: `Bearer ${this.apiKey}` } : {}),
      },
      body: JSON.stringify({
        model: request.preferredModel ?? this.model,
        messages: request.messages,
      }),
    });

    if (response.status === 429) {
      const retryAfter = response.headers.get("retry-after");
      const retryAfterMs = retryAfter && /^\d+$/.test(retryAfter)
        ? Number(retryAfter) * 1000
        : undefined;
      throw new ProviderRateLimitError("Provider quota/rate limit reached.", retryAfterMs);
    }

    if (!response.ok) {
      throw new Error(`Provider ${this.id} failed with HTTP ${response.status}.`);
    }

    const payload = await response.json() as {
      model?: string;
      choices?: Array<{ message?: { content?: string } }>;
    };
    const content = payload.choices?.[0]?.message?.content;
    if (typeof content !== "string") {
      throw new Error(`Provider ${this.id} returned an invalid chat completion.`);
    }

    return {
      provider: this.id,
      model: payload.model ?? request.preferredModel ?? this.model,
      content,
    };
  }
}
