"use client";

import { useState } from "react";

import { deleteSession } from "../lib/api";

export function DeleteButton({ sessionId }: { sessionId: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDelete = async () => {
    if (busy) return;
    const confirmed = window.confirm("Delete this analysis session and return home?");
    if (!confirmed) {
      return;
    }

    try {
      setBusy(true);
      setError(null);
      await deleteSession(sessionId);
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete this session right now.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel panel-soft danger-zone">
      <h3 className="section-title">Session controls</h3>
      <p className="section-note">Remove this session and all associated uploaded photos.</p>
      <div className="actions">
        <button className="button button-ghost button-danger" onClick={onDelete} disabled={busy}>
          Delete Session
        </button>
      </div>
      {error ? <p className="status-line status-error">{error}</p> : null}
    </section>
  );
}
