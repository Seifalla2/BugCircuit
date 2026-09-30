import type { ModelRequest, ModelResponse, Provider } from "./types.js";

export class NoProviderAvailableError extends Error {
  constructor() {
    super("No AI provider is currently available.");
    this.name = "NoProviderAvailableError";
  }
}

export class ProviderRouter {
  constructor(private readonly providers: Provider[]) {}

  async complete(request: ModelRequest): Promise<ModelResponse> {
    for (const provider of this.providers) {
      if (!(await provider.isAvailable())) continue;
      try {
        return await provider.complete(request);
      } catch {
        // Provider failures are isolated; the next provider gets a chance.
      }
    }
    throw new NoProviderAvailableError();
  }
}
