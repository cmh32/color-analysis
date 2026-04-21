"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { GuidanceChecklist } from "../../components/GuidanceChecklist";
import { Upload } from "../../components/Upload";
import { ProgressSpinner } from "../../components/ProgressSpinner";
import { getStatus } from "../../lib/api";
import { saveSessionId } from "../../lib/session";

type ErrorInfo = { heading: string; detail: string };

export default function AnalyzePage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState("Analyzing...");
  const [errorInfo, setErrorInfo] = useState<ErrorInfo | null>(null);

  const handleSessionReady = (id: string) => {
    saveSessionId(id);
    setErrorInfo(null);
    setStatusMessage("Analyzing...");
    setSessionId(id);
  };

  const handleRetry = () => {
    setSessionId(null);
    setErrorInfo(null);
  };

  useEffect(() => {
    if (!sessionId) return;

    let active = true;
    let attempt = 0;
    const MAX_ATTEMPTS = 120;

    const poll = async () => {
      if (!active) return;
      if (attempt >= MAX_ATTEMPTS) {
        setErrorInfo({
          heading: "Analysis timed out",
          detail: "The analysis is taking too long. Please try again.",
        });
        return;
      }

      attempt += 1;
      const delay = Math.min(1500 * Math.pow(1.2, Math.floor(attempt / 10)), 10000);

      try {
        const status = await getStatus(sessionId);
        if (!active) return;

        if (status.status === "complete") {
          if (status.result_state === "insufficient_photos") {
            setErrorInfo({
              heading: "Not enough usable photos",
              detail:
                "At least 6 clear face photos are required. Try again with better lighting, a direct angle, and no sunglasses.",
            });
            return;
          }
          router.push(`/result/${sessionId}`);
          return;
        }

        if (status.status === "failed") {
          setErrorInfo({
            heading: "Analysis failed",
            detail: "Something went wrong on our end. Please try again.",
          });
          return;
        }

        setStatusMessage(`Status: ${status.status}`);
      } catch {
        // network blip — keep polling
      }

      window.setTimeout(poll, delay);
    };

    void poll();
    return () => {
      active = false;
    };
  }, [router, sessionId]);

  const isPolling = sessionId !== null && errorInfo === null;

  return (
    <main>
      <h1>Analyze</h1>
      <GuidanceChecklist />
      {!isPolling && !errorInfo && <Upload onSessionReady={handleSessionReady} />}
      {isPolling && <ProgressSpinner message={statusMessage} />}
      {errorInfo && (
        <section className="card">
          <h3>{errorInfo.heading}</h3>
          <p>{errorInfo.detail}</p>
          <button onClick={handleRetry}>Try again</button>
        </section>
      )}
    </main>
  );
}
