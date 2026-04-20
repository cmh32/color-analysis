import type { ClassificationResult } from "@color-analysis/shared-types";
import { AxisDials } from "./AxisDials";
import { ReliabilityBadge } from "./ReliabilityBadge";
import { HowWeMeasured } from "./HowWeMeasured";
import { DeleteButton } from "./DeleteButton";

export function ResultScreen({ result }: { result: ClassificationResult }) {
  return (
    <>
      <section className="card">
        <h2>Top Result: {result.top_2_seasons[0]}</h2>
        <p>Also likely: {result.top_2_seasons[1]}</p>
        <p>State: {result.result_state}</p>
      </section>
      <AxisDials scorecard={result.scorecard} />
      <ReliabilityBadge reliability={result.reliability} />
      <HowWeMeasured traces={result.trace} />
      <DeleteButton sessionId={result.session_id} />
    </>
  );
}
