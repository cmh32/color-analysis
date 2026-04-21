import type { CSSProperties } from "react";
import type { Scorecard } from "../lib/types";

type AxisEntry = {
  key: keyof Scorecard;
  label: string;
  rangeLabel: string;
  fillClass: string;
};

const ENTRIES: AxisEntry[] = [
  {
    key: "warmth",
    label: "Warmth",
    rangeLabel: "Cool to warm",
    fillClass: "axis-fill-warmth"
  },
  {
    key: "value",
    label: "Value",
    rangeLabel: "Deep to light",
    fillClass: "axis-fill-value"
  },
  {
    key: "chroma",
    label: "Chroma",
    rangeLabel: "Soft to vivid",
    fillClass: "axis-fill-chroma"
  },
  {
    key: "contrast",
    label: "Contrast",
    rangeLabel: "Low to high",
    fillClass: "axis-fill-contrast"
  }
];

export function AxisDials({ scorecard }: { scorecard: Scorecard }) {
  return (
    <section className="panel">
      <h3 className="section-title">Attribute profile</h3>
      <p className="section-note">Normalized scores across the four color-analysis axes.</p>
      <div className="axis-grid" style={{ marginTop: "0.85rem" }}>
        {ENTRIES.map(({ key, label, rangeLabel, fillClass }) => {
          const raw = scorecard[key];
          const percent = Math.max(0, Math.min(100, Math.round(((raw + 1) / 2) * 100)));
          const meterStyle = { "--fill": `${percent}%` } as CSSProperties;

          return (
            <article className="axis-card" key={key}>
              <div className="axis-meta">
                <strong>{label}</strong>
                <span className="axis-value">{raw.toFixed(2)}</span>
              </div>
              <div className="axis-track">
                <div className={`axis-fill ${fillClass}`} style={meterStyle} />
              </div>
              <p className="axis-range" style={{ marginTop: "0.42rem" }}>
                {rangeLabel}
              </p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
