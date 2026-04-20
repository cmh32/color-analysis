import type { Reliability } from "@color-analysis/shared-types";

export function ReliabilityBadge({ reliability }: { reliability: Reliability }) {
  return (
    <section className="card">
      <h3>Reliability: {reliability.bucket}</h3>
      <p>Score: {reliability.score.toFixed(3)}</p>
      <ul>
        {reliability.reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
    </section>
  );
}
