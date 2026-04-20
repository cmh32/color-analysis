import type { Scorecard } from "@color-analysis/shared-types";

export function AxisDials({ scorecard }: { scorecard: Scorecard }) {
  const entries: Array<[keyof Scorecard, string]> = [
    ["warmth", "Warmth"],
    ["value", "Value"],
    ["chroma", "Chroma"],
    ["contrast", "Contrast"]
  ];

  return (
    <section className="card">
      <h3>Axis Dials</h3>
      {entries.map(([key, label]) => {
        const raw = scorecard[key];
        const percent = Math.round(((raw + 1) / 2) * 100);
        return (
          <div key={key} style={{ marginBottom: "0.75rem" }}>
            <strong>{label}</strong>
            <div
              style={{
                height: "8px",
                borderRadius: "8px",
                background: "#e5e7eb",
                marginTop: "0.35rem"
              }}
            >
              <div
                style={{
                  height: "100%",
                  borderRadius: "8px",
                  width: `${percent}%`,
                  background: "var(--accent)"
                }}
              />
            </div>
          </div>
        );
      })}
    </section>
  );
}
