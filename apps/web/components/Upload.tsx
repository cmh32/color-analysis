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
  const [fileCount, setFileCount] = useState(0);

  const onFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    setFileCount(files.length);

    if (files.length < 6 || files.length > 15) {
      setError("Upload between 6 and 15 photos to analyze.");
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
    <section className="panel upload-panel">
      <h3 className="section-title">Upload your photo set</h3>
      <p className="section-note">
        Select 6 to 15 selfies captured in natural light for your most consistent profile.
      </p>

      <label className={`upload-field${busy ? " is-disabled" : ""}`}>
        <span className="upload-field-label">Choose photos</span>
        <span className="upload-field-hint">Accepted: JPG, PNG, HEIC, HEIF</span>
        <input
          className="visually-hidden"
          type="file"
          accept="image/*"
          multiple
          onChange={onFileChange}
          disabled={busy}
        />
      </label>

      {fileCount > 0 ? (
        <p className="status-line">
          <strong>{fileCount}</strong> photo{fileCount === 1 ? "" : "s"} selected
        </p>
      ) : null}

      {busy ? <p className="status-line">{statusMessage}</p> : null}
      {error ? <p className="status-line status-error">{error}</p> : null}
    </section>
  );
}
