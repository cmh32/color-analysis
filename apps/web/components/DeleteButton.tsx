"use client";

import { deleteSession } from "../lib/api";

export function DeleteButton({ sessionId }: { sessionId: string }) {
  const onDelete = async () => {
    await deleteSession(sessionId);
    window.location.href = "/";
  };

  return <button onClick={onDelete}>Delete Session</button>;
}
