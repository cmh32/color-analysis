export function ProgressSpinner({ message }: { message: string }) {
  return (
    <section className="card" aria-live="polite">
      <h3>Analyzing</h3>
      <p>{message}</p>
    </section>
  );
}
