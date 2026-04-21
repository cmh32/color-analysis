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
  const [statusMessage, setStatusMessage] = useState("Preparing analysis...");
  const [error, setError] = useState<string | null>(null);

  const onFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (files.length < 6) {
      setError("Upload at least 6 photos to analyze.");
      return;
    }

    setBusy(true);
    setStatusMessage("Creating analysis session...");
    setError(null);

    try {
      const session = await createSession();
      const total = files.length;
      const uploads: Array<{
        file: File;
        uploadUrl: string;
        uploadFields: Record<string, string>;
      }> = [];

      for (let index = 0; index < files.length; index += 1) {
        const file = files[index];
        setStatusMessage(`Registering photos (${index + 1}/${total})...`);
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

        uploads.push({
          file,
          uploadUrl: registration.upload_url,
          uploadFields: registration.upload_fields
        });
      }
      for (let index = 0; index < uploads.length; index += 1) {
        setStatusMessage(`Uploading photos (${index + 1}/${total})...`);
        const { file, uploadUrl, uploadFields } = uploads[index];
        await uploadPhoto(uploadUrl, uploadFields, file);
      }

      setStatusMessage("Starting analysis...");
      await runAnalysis(session.id);
      onSessionReady(session.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
      setStatusMessage("Preparing analysis...");
    }
  };

  return (
    <section className="card">
      <h3>Upload Photos</h3>
      <input type="file" accept="image/*" multiple onChange={onFileChange} disabled={busy} />
      {busy ? <p>{statusMessage}</p> : null}
      {error ? <p style={{ color: "#b91c1c" }}>{error}</p> : null}
    </section>
  );
}
