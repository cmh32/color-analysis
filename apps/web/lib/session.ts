const SESSION_KEY = "color-analysis-session";

export function saveSessionId(sessionId: string): void {
  localStorage.setItem(SESSION_KEY, sessionId);
}

export function loadSessionId(): string | null {
  return localStorage.getItem(SESSION_KEY);
}
