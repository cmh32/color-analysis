import type {
  ApiErrorCode,
  ClassificationResult,
  PhotoRejectionReason,
  ProblemDetail,
  SessionReviewResponse,
  StatusResponse,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const API_REQUEST_TIMEOUT_MS = 30_000;
const UPLOAD_REQUEST_TIMEOUT_MS = 180_000;

type PhotoRegisterResponse = {
  id: string;
  accepted: boolean;
  reasons: PhotoRejectionReason[];
  upload_url?: string | null;
  upload_fields?: Record<string, string> | null;
};

const ERROR_TYPE_PREFIX = "https://errors.color-analysis.local/";
const FALLBACK_API_ERROR_CODE: ApiErrorCode = "internal_error";

const API_ERROR_MESSAGES: Record<ApiErrorCode, string> = {
  invalid_session: "This session is invalid. Start a new upload and try again.",
  session_not_found: "This session is no longer available. Start a new upload and try again.",
  session_deleted: "This session was deleted. Start a new upload and try again.",
  insufficient_photos: "At least 6 clear photos are required before analysis can start.",
  already_running: "Analysis is already running for this session. Please wait for it to finish.",
  already_complete: "This session is already complete. Start a new upload to run again.",
  result_not_ready: "Your result is still being prepared. Retry in a few moments.",
  forbidden: "You are not authorized to perform this action.",
  invalid_request: "The request was invalid. Please refresh and retry.",
  internal_error: "Server error while processing your request. Please retry.",
  rate_limit_exceeded: "Too many attempts in a short time. Wait a minute and retry."
};

function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === "AbortError";
}

async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number,
  operation: string
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (error) {
    if (isAbortError(error)) {
      throw new Error(`${operation} timed out after ${Math.round(timeoutMs / 1000)}s`);
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

function truncate(text: string, maxLength: number = 180): string {
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
}

function extractErrorType(problem: { type?: string }): string | null {
  if (!problem.type?.startsWith(ERROR_TYPE_PREFIX)) {
    return null;
  }
  return problem.type.slice(ERROR_TYPE_PREFIX.length);
}

function asApiErrorCode(value: string | null): ApiErrorCode | null {
  if (!value) return null;
  if (value in API_ERROR_MESSAGES) {
    return value as ApiErrorCode;
  }
  return null;
}

function mapProblemToMessage(problem: Partial<ProblemDetail>, statusCode: number): string {
  const structuredCode = typeof problem.error_code === "string" ? asApiErrorCode(problem.error_code) : null;
  const typeCode = asApiErrorCode(extractErrorType(problem));
  const errorCode = structuredCode ?? typeCode ?? (statusCode >= 500 ? FALLBACK_API_ERROR_CODE : null);

  if (errorCode) {
    return API_ERROR_MESSAGES[errorCode];
  }
  if (problem.detail) {
    return truncate(problem.detail);
  }
  return `Request failed with HTTP ${statusCode}.`;
}

async function buildApiError(response: Response): Promise<Error> {
  let bodyText = "";
  try {
    bodyText = await response.text();
  } catch {
    bodyText = "";
  }

  if (bodyText) {
    try {
      const parsed = JSON.parse(bodyText) as Partial<ProblemDetail>;
      if (parsed && typeof parsed === "object") {
        return new Error(mapProblemToMessage(parsed, response.status));
      }
    } catch {
      return new Error(`API request failed (HTTP ${response.status}): ${truncate(bodyText)}`);
    }
  }

  return new Error(`API request failed (HTTP ${response.status}).`);
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}${path}`,
    {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {})
      },
      cache: "no-store"
    },
    API_REQUEST_TIMEOUT_MS,
    `API request to ${path}`
  );

  if (!response.ok) {
    throw await buildApiError(response);
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
): Promise<PhotoRegisterResponse> {
  return call(`/v1/sessions/${sessionId}/photos`, {
    method: "POST",
    body: JSON.stringify({ filename, mime_type: mimeType, size_bytes: sizeBytes })
  });
}

export async function uploadPhoto(
  uploadUrl: string,
  uploadFields: Record<string, string>,
  file: File
): Promise<void> {
  const form = new FormData();
  for (const [key, value] of Object.entries(uploadFields)) {
    form.append(key, value);
  }
  form.append("file", file);

  let response: Response;
  try {
    response = await fetchWithTimeout(
      uploadUrl,
      {
        method: "POST",
        body: form
      },
      UPLOAD_REQUEST_TIMEOUT_MS,
      `Upload for ${file.name}`
    );
  } catch (error) {
    const reason = error instanceof Error ? error.message : "Unknown network error";
    throw new Error(
      `Photo upload failed before server response. Check storage connectivity/CORS and retry. (${reason})`
    );
  }

  if (!response.ok) {
    const text = await response.text();
    if (response.status === 403) {
      throw new Error("Photo upload credentials expired or were rejected. Retry the upload.");
    }
    if (response.status === 413) {
      throw new Error("Photo upload was rejected because the file is too large.");
    }
    throw new Error(`Photo upload failed at storage (HTTP ${response.status}). ${truncate(text || "No response body")}`);
  }
}

export async function runAnalysis(sessionId: string): Promise<{ accepted: boolean }> {
  return call(`/v1/sessions/${sessionId}/analyze`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function getStatus(sessionId: string): Promise<StatusResponse> {
  return call(`/v1/sessions/${sessionId}/status`);
}

export async function getResult(sessionId: string): Promise<ClassificationResult> {
  return call(`/v1/sessions/${sessionId}/result`);
}

export async function getReview(sessionId: string): Promise<SessionReviewResponse> {
  return call(`/v1/sessions/${sessionId}/review`);
}

export async function deleteSession(sessionId: string): Promise<void> {
  await call(`/v1/sessions/${sessionId}`, { method: "DELETE" });
}
