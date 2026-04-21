import type { ClassificationResult } from "../lib/types";
import { AxisDials } from "./AxisDials";
import { ColorSwatches } from "./ColorSwatches";
import { DeleteButton } from "./DeleteButton";
import { HowWeMeasured } from "./HowWeMeasured";
import { MeasurementExplanation } from "./MeasurementExplanation";
import { ReliabilityBadge } from "./ReliabilityBadge";

type SeasonTone = {
  label: string;
  toneClass: string;
};

const SEASON_TONE: Record<ClassificationResult["top_2_seasons"][number], SeasonTone> = {
  Spring: { label: "Bright, warm, and fresh", toneClass: "tone-butter" },
  Summer: { label: "Soft, cool, and airy", toneClass: "tone-powder" },
  Autumn: { label: "Rich, warm, and earthy", toneClass: "tone-sage" },
  Winter: { label: "High contrast, cool, and crisp", toneClass: "tone-lilac" }
};

export function ResultScreen({ result }: { result: ClassificationResult }) {
  const topSeason = result.top_2_seasons[0];
  const altSeason = result.top_2_seasons[1];

  return (
    <>
      <section className="panel result-hero">
        <h2>{topSeason}</h2>
        <p className="section-note">Primary alignment: {topSeason}</p>
        <p className="section-note">Secondary alignment: {altSeason}</p>
        <div className="result-season">
          {[topSeason, altSeason].map((season) => (
            <article className="swatch-card" key={season}>
              <div className={`swatch-chip ${SEASON_TONE[season].toneClass}`} />
              <strong>{season}</strong>
              <p className="section-note">{SEASON_TONE[season].label}</p>
            </article>
          ))}
        </div>
      </section>

      <AxisDials scorecard={result.scorecard} />
      <MeasurementExplanation explanation={result.measurement_explanation ?? null} />
      <ColorSwatches swatches={result.color_swatches ?? null} />
      <ReliabilityBadge reliability={result.reliability} />
      {result.trace.length > 0 ? <HowWeMeasured traces={result.trace} /> : null}
      <DeleteButton sessionId={result.session_id} />
    </>
  );
}
