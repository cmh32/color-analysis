import type { ClassificationResult } from "../lib/types";

const LABELS: Record<string, string> = { skin: "Skin tone", iris: "Iris", hair: "Hair" };
const ORDER = ["skin", "iris", "hair"] as const;

export function ColorSwatches({
  swatches,
}: {
  swatches: ClassificationResult["color_swatches"];
}) {
  if (!swatches) return null;
  const entries = ORDER.filter((k) => k in swatches);
  if (entries.length === 0) return null;

  return (
    <section className="panel">
      <h3 className="section-title">Your measured colors</h3>
      <p className="section-note">Colors extracted by CV from your photos.</p>
      <div className="result-season" style={{ marginTop: "0.85rem" }}>
        {entries.map((key) => (
          <article className="swatch-card" key={key}>
            <div className="swatch-chip" style={{ backgroundColor: swatches[key] }} />
            <strong>{LABELS[key]}</strong>
            <p className="section-note" style={{ fontFamily: "monospace" }}>
              {swatches[key]}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
