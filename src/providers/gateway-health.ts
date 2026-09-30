export interface GatewayHealth {
  ok: boolean;
  status: number;
  models: string[];
}

export async function checkOpenAICompatibleGateway(
  baseUrl: string,
  apiKey?: string,
  fetchImpl: typeof fetch = fetch,
): Promise<GatewayHealth> {
  const normalized = baseUrl.replace(/\/$/, "");
  try {
    const response = await fetchImpl(`${normalized}/models`, {
      headers: apiKey ? { authorization: `Bearer ${apiKey}` } : {},
    });
    if (!response.ok) return { ok: false, status: response.status, models: [] };

    const body = await response.json() as { data?: Array<{ id?: string }> };
    return {
      ok: true,
      status: response.status,
      models: (body.data ?? []).flatMap((item) => typeof item.id === "string" ? [item.id] : []),
    };
  } catch {
    return { ok: false, status: 0, models: [] };
  }
}
