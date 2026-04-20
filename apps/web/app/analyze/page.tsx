"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { GuidanceChecklist } from "../../components/GuidanceChecklist";
import { Upload } from "../../components/Upload";
import { ProgressSpinner } from "../../components/ProgressSpinner";
import { getStatus } from "../../lib/api";
import { saveSessionId } from "../../lib/session";

export default function AnalyzePage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [message, setMessage] = useState("Waiting for uploads...");

  useEffect(() => {
    if (!sessionId) {
      return;
    }

    saveSessionId(sessionId);
    let active = true;

    const poll = async () => {
      const status = await getStatus(sessionId);
      if (!active) {
        return;
      }

      setMessage(`Status: ${status.status}`);
      if (status.status === "complete") {
        if (status.result_state === "insufficient_photos") {
          setMessage(
            "Not enough usable photos — at least 6 clear face photos are required. Please try again with better lighting and a direct angle."
          );
          return;
        }
        router.push(`/result/${sessionId}`);
        return;
      }
      if (status.status === "failed") {
        setMessage("Analysis failed. Please retry with new photos.");
        return;
      }

      window.setTimeout(poll, 1500);
    };

    void poll();
    return () => {
      active = false;
    };
  }, [router, sessionId]);

  return (
    <main>
      <h1>Analyze</h1>
      <GuidanceChecklist />
      <Upload onSessionReady={setSessionId} />
      {sessionId ? <ProgressSpinner message={message} /> : null}
    </main>
  );
}
