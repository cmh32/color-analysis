"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ResultScreen } from "../../../components/ResultScreen";
import { getResult } from "../../../lib/api";
import type { ClassificationResult } from "../../../lib/types";

export default function ResultPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params.sessionId;
  const [result, setResult] = useState<ClassificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [requestVersion, setRequestVersion] = useState(0);

  useEffect(() => {
    let active = true;
    setError(null);
    setResult(null);
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
  }, [sessionId, requestVersion]);

  return (
    <main className="page">
      <section className="hero">
        <span className="eyebrow">Result</span>
        <h1>Your Seasonal Color Report</h1>
        <p className="lede">
          This profile combines your uploaded photo set into a top seasonal match and a
          confidence summary.
        </p>
      </section>

      {error ? (
        <section className="panel panel-error">
          <h3 className="section-title">Unable to load your result</h3>
          <p className="status-error">{error}</p>
          <div className="actions">
            <button className="button button-primary" onClick={() => setRequestVersion((value) => value + 1)}>
              Retry
            </button>
          </div>
        </section>
      ) : null}

      {result ? (
        <ResultScreen result={result} />
      ) : !error ? (
        <section className="panel panel-soft">
          <p className="loading-copy">Preparing your report...</p>
        </section>
      ) : null}
    </main>
  );
}
