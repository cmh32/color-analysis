"use client";

import { useState } from "react";
import { createSession, registerPhoto, runAnalysis } from "../lib/api";

export function Upload({ onSessionReady }: { onSessionReady: (sessionId: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (files.length < 6) {
      setError("Upload at least 6 photos to analyze.");
      return;
    }

    setBusy(true);
    setError(null);

    try {
      const session = await createSession();
      for (const file of files) {
        await registerPhoto(session.id, file.name, file.type || "image/jpeg", file.size);
      }
      await runAnalysis(session.id);
      onSessionReady(session.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card">
      <h3>Upload Photos</h3>
      <input type="file" accept="image/*" multiple onChange={onFileChange} disabled={busy} />
      {busy ? <p>Preparing analysis...</p> : null}
      {error ? <p style={{ color: "#b91c1c" }}>{error}</p> : null}
    </section>
  );
}
