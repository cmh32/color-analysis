"use client";

import { useState } from "react";
import { createSession, registerPhoto, runAnalysis, uploadPhoto } from "../lib/api";

const WRONG_FILE_TYPE_MESSAGE =
  "Whoops - one or more of your pictures are not the right file type. Please upload JPG, PNG, HEIC, or HEIF files. You're so close to your personalized color profile.";

const ALLOWED_MIME_TYPES = new Set([
  "image/jpeg",
  "image/jpg",
  "image/png",
  "image/heic",
  "image/heif"
]);

function hasAllowedExtension(filename: string): boolean {
  const lower = filename.toLowerCase();
  return (
    lower.endsWith(".jpg") ||
    lower.endsWith(".jpeg") ||
    lower.endsWith(".png") ||
    lower.endsWith(".heic") ||
    lower.endsWith(".heif")
  );
}

function isSupportedPhotoFile(file: File): boolean {
  const mimeType = file.type.toLowerCase();
  if (ALLOWED_MIME_TYPES.has(mimeType)) {
    return true;
  }
  return hasAllowedExtension(file.name);
}

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
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [canRetry, setCanRetry] = useState(false);

  const mapPhotoRegistrationError = (reasons: string[]): string => {
    const normalizedReasons = reasons.map((reason) => reason.toLowerCase());
    if (normalizedReasons.some((reason) => reason.includes("mime") || reason.includes("type"))) {
      return WRONG_FILE_TYPE_MESSAGE;
    }
    if (normalizedReasons.includes("photo_limit_exceeded")) {
      return "This upload session reached the 15-photo limit. Choose files again to start a new session.";
    }
    if (normalizedReasons.includes("session_not_pending")) {
      return "This session is no longer accepting uploads. Start a new upload and retry.";
    }
    if (normalizedReasons.includes("invalid_filename")) {
      return "One file name is invalid. Rename that file (remove path-like characters) and retry.";
    }
    return `Photo rejected: ${reasons.join(", ")}`;
  };

  const beginUpload = async (files: File[]) => {
    setFileCount(files.length);
    setCanRetry(false);
    if (files.length === 0) {
      setError("Please choose 6 to 15 photos to begin.");
      return;
    }

    const hasUnsupportedType = files.some((file) => !isSupportedPhotoFile(file));
    const hasEmptyFile = files.some((file) => file.size <= 0);

    if (hasUnsupportedType) {
      setError(WRONG_FILE_TYPE_MESSAGE);
      return;
    }
    if (hasEmptyFile) {
      setError("One selected file is empty. Please remove it and try again.");
      return;
    }

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
          throw new Error(mapPhotoRegistrationError(registration.reasons));
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
      setCanRetry(true);
    } finally {
      setBusy(false);
      setStatusMessage("Preparing analysis...");
    }
  };

  const onFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    setSelectedFiles(files);
    await beginUpload(files);
  };

  return (
    <section className="panel upload-panel">
      <h3 className="section-title upload-title">Upload your photo set</h3>
      <p className="section-note">
        Select 6 to 15 selfies captured in natural light for your most consistent profile.
      </p>

      <label className={`upload-field${busy ? " is-disabled" : ""}`}>
        <span className="upload-field-label">Choose photos</span>
        <span className="upload-field-hint">You can upload a JPG, PNG, HEIC, or HEIF</span>
        <input
          className="visually-hidden"
          type="file"
          accept=".jpg,.jpeg,.png,.heic,.heif,image/jpeg,image/png,image/heic,image/heif"
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
      {canRetry && !busy ? (
        <div className="actions">
          <button className="button button-primary" onClick={() => void beginUpload(selectedFiles)}>
            Retry Upload
          </button>
        </div>
      ) : null}
    </section>
  );
}
