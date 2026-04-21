import type { Reliability } from "../lib/types";

const BUCKET_CLASS: Record<Reliability["bucket"], string> = {
  High: "pill-high",
  Medium: "pill-medium",
  Low: "pill-low"
};

export function ReliabilityBadge({ reliability }: { reliability: Reliability }) {
  return (
    <section className="panel panel-soft">
      <div className="reliability-header">
        <h3>Confidence</h3>
        <span className={`pill ${BUCKET_CLASS[reliability.bucket]}`}>{reliability.bucket}</span>
      </div>
      <p className="section-note">
        Composite score: <strong>{reliability.score.toFixed(3)}</strong>
      </p>
      <ul className="reason-list">
        {reliability.reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
    </section>
  );
}
