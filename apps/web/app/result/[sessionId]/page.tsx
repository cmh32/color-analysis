"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import type { ClassificationResult } from "@color-analysis/shared-types";
import { ResultScreen } from "../../../components/ResultScreen";
import { getResult } from "../../../lib/api";

export default function ResultPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params.sessionId;
  const [result, setResult] = useState<ClassificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void getResult(sessionId)
      .then((payload) => {
        if (active) {
          setResult(payload);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Unable to fetch result");
        }
      });

    return () => {
      active = false;
    };
  }, [sessionId]);

  return (
    <main>
      <h1>Result</h1>
      {error ? <p style={{ color: "#b91c1c" }}>{error}</p> : null}
      {result ? <ResultScreen result={result} /> : <p>Loading result...</p>}
    </main>
  );
}
