import type { ClassificationResult } from "../lib/types";

const LABELS: Record<string, string> = { skin: "Skin tone", iris: "Iris", hair: "Hair" };
const ORDER = ["skin", "iris", "hair"] as const;

export function ColorSwatches({
  swatches,
}: {
  swatches: ClassificationResult["color_swatches"];
}) {
  if (!swatches) return null;

  return (
    <section className="panel">
      <h3 className="section-title">Your measured colors</h3>
      <p className="section-note">Colors extracted by CV from your photos.</p>
      <div className="result-season" style={{ marginTop: "0.85rem" }}>
        {ORDER.map((key) => {
          const hex = swatches[key];
          if (hex) {
            return (
              <article className="swatch-card" key={key}>
                <div className="swatch-chip" style={{ backgroundColor: hex }} />
                <strong>{LABELS[key]}</strong>
                <p className="section-note" style={{ fontFamily: "monospace" }}>
                  {hex}
                </p>
              </article>
            );
          }
          return (
            <article className="swatch-card" key={key} style={{ opacity: 0.5 }}>
              <div
                className="swatch-chip"
                style={{
                  background:
                    "repeating-linear-gradient(45deg, #ccc 0px, #ccc 4px, #eee 4px, #eee 8px)",
                }}
              />
              <strong>{LABELS[key]}</strong>
              <p className="section-note">couldn&apos;t measure</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
