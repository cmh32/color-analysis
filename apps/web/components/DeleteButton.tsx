"use client";

import { deleteSession } from "../lib/api";

export function DeleteButton({ sessionId }: { sessionId: string }) {
  const onDelete = async () => {
    const confirmed = window.confirm("Delete this analysis session and return home?");
    if (!confirmed) {
      return;
    }

    await deleteSession(sessionId);
    window.location.href = "/";
  };

  return (
    <section className="panel panel-soft danger-zone">
      <h3 className="section-title">Session controls</h3>
      <p className="section-note">Remove this session and all associated uploaded photos.</p>
      <div className="actions">
        <button className="button button-ghost button-danger" onClick={onDelete}>
          Delete Session
        </button>
      </div>
    </section>
  );
}
