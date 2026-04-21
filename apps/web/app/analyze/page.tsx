"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { GuidanceChecklist } from "../../components/GuidanceChecklist";
import { Upload } from "../../components/Upload";
import { ProgressSpinner } from "../../components/ProgressSpinner";
import { getStatus } from "../../lib/api";
import { saveSessionId } from "../../lib/session";

type ErrorInfo = { heading: string; detail: string };

const STATUS_LABELS: Record<string, string> = {
  pending: "Queueing your analysis session...",
  running: "Reviewing your color attributes...",
  complete: "Finalizing your profile..."
};

const RETRYABLE_RESULT_STATES: Record<string, ErrorInfo> = {
  insufficient_photos: {
    heading: "Not enough usable photos",
    detail: "At least 6 clear face photos are required. Retry with brighter lighting and direct angles."
  },
  no_face_detected: {
    heading: "Could not detect a face",
    detail: "Use well-lit, front-facing photos with one visible face and try again."
  },
  multiple_subjects: {
    heading: "Multiple faces detected",
    detail: "Upload photos with only one person in frame, then retry."
  },
  filter_suspected: {
    heading: "Photo filters detected",
    detail: "Please retry with unfiltered original photos."
  }
};

export default function AnalyzePage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState("Preparing your analysis...");
  const [errorInfo, setErrorInfo] = useState<ErrorInfo | null>(null);

  const handleSessionReady = (id: string) => {
    saveSessionId(id);
    setErrorInfo(null);
    setStatusMessage("Preparing your analysis...");
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
    let consecutiveErrors = 0;
    const MAX_ATTEMPTS = 120;
    const MAX_NETWORK_ERRORS = 8;

    const poll = async () => {
      if (!active) return;
      if (attempt >= MAX_ATTEMPTS) {
        setErrorInfo({
          heading: "Analysis timed out",
          detail: "This session is taking too long. Please start a new upload."
        });
        return;
      }

      attempt += 1;
      const delay = Math.min(1500 * Math.pow(1.2, Math.floor(attempt / 10)), 10000);

      try {
        const status = await getStatus(sessionId);
        if (!active) return;
        consecutiveErrors = 0;

        if (status.status === "complete") {
          const retryableError =
            status.result_state !== null ? RETRYABLE_RESULT_STATES[status.result_state] : undefined;
          if (retryableError) {
            setErrorInfo(retryableError);
            return;
          }
          router.push(`/result/${sessionId}`);
          return;
        }

        if (status.status === "failed") {
          setErrorInfo({
            heading: "Analysis failed",
            detail: "Something went wrong on our side. Please try again shortly."
          });
          return;
        }

        setStatusMessage(STATUS_LABELS[status.status] ?? `Status: ${status.status}`);
      } catch {
        consecutiveErrors += 1;
        if (consecutiveErrors >= MAX_NETWORK_ERRORS) {
          setErrorInfo({
            heading: "Connection problem",
            detail: "We lost connection while checking progress. Please try again."
          });
          return;
        }
        setStatusMessage("Connection issue while checking progress. Retrying...");
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
    <main className="page">
      <section className="hero">
        <span className="eyebrow">Analyze</span>
        <h1>Build your personalized color profile.</h1>
        <p className="lede">
          Upload a curated set of selfies and we will estimate your top seasonal family,
          confidence level, and measurement trace.
        </p>
      </section>

      {!isPolling && !errorInfo && <Upload onSessionReady={handleSessionReady} />}
      {!isPolling && !errorInfo && <GuidanceChecklist />}
      {isPolling && <ProgressSpinner message={statusMessage} />}

      {errorInfo && (
        <section className="panel panel-error">
          <h3 className="section-title">{errorInfo.heading}</h3>
          <p className="section-note">{errorInfo.detail}</p>
          <div className="actions">
            <button className="button button-primary" onClick={handleRetry}>
              Try Again
            </button>
          </div>
        </section>
      )}
    </main>
  );
}
