import type { ClassificationResult } from "@color-analysis/shared-types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API request failed: ${response.status} ${text}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function createSession(): Promise<{ id: string; status: string }> {
  return call("/v1/sessions", { method: "POST" });
}

export async function registerPhoto(
  sessionId: string,
  filename: string,
  mimeType: string,
  sizeBytes: number
): Promise<{ id: string; accepted: boolean; reasons: string[] }> {
  return call(`/v1/sessions/${sessionId}/photos`, {
    method: "POST",
    body: JSON.stringify({ filename, mime_type: mimeType, size_bytes: sizeBytes })
  });
}

export async function runAnalysis(sessionId: string): Promise<{ accepted: boolean }> {
  return call(`/v1/sessions/${sessionId}/analyze`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function getStatus(
  sessionId: string
): Promise<{ status: string; result_state: string | null }> {
  return call(`/v1/sessions/${sessionId}/status`);
}

export async function getResult(sessionId: string): Promise<ClassificationResult> {
  return call(`/v1/sessions/${sessionId}/result`);
}

export async function deleteSession(sessionId: string): Promise<void> {
  await call(`/v1/sessions/${sessionId}`, { method: "DELETE" });
}
