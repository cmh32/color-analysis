export function ProgressSpinner({ message }: { message: string }) {
  return (
    <section className="panel panel-soft progress-panel" aria-live="polite">
      <div className="spinner" />
      <h3 className="section-title">Curating your profile</h3>
      <p className="status-line">{message}</p>
    </section>
  );
}
