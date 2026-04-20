"use client";

import { useState } from "react";
import { createSession, registerPhoto, runAnalysis, uploadPhoto } from "../lib/api";

function inferMimeType(file: File): string {
  if (file.type) {
    return file.type;
  }

  const lower = file.name.toLowerCase();
  if (lower.endsWith(".heic")) {
    return "image/heic";
  }
  if (lower.endsWith(".heif")) {
    return "image/heif";
  }
  if (lower.endsWith(".png")) {
    return "image/png";
  }
  return "image/jpeg";
}

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
        const registration = await registerPhoto(
          session.id,
          file.name,
          inferMimeType(file),
          file.size
        );

        if (!registration.accepted) {
          throw new Error(`Photo rejected: ${registration.reasons.join(", ")}`);
        }
        if (!registration.upload_url || !registration.upload_fields) {
          throw new Error("Photo registration did not return upload credentials");
        }

        await uploadPhoto(registration.upload_url, registration.upload_fields, file);
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
