export type Season = "Spring" | "Summer" | "Autumn" | "Winter";

export interface Scorecard {
  warmth: number;
  value: number;
  chroma: number;
  contrast: number;
}

export interface Reliability {
  score: number;
  bucket: "High" | "Medium" | "Low";
  reasons: string[];
}

export interface ClassificationResult {
  session_id: string;
  top_2_seasons: Season[];
  scorecard: Scorecard;
  reliability: Reliability;
  result_state:
    | "ok"
    | "ok_low_reliability"
    | "insufficient_photos"
    | "no_face_detected"
    | "multiple_subjects"
    | "filter_suspected"
    | "failed";
  trace: string[];
}
