import type { components } from "@color-analysis/shared-types";

export type ClassificationResult = components["schemas"]["AnalysisResult"];
export type Scorecard = components["schemas"]["Scorecard"];
export type Reliability = components["schemas"]["Reliability"];
export type RejectedPhotoReview = components["schemas"]["RejectedPhotoReview"];
export type SessionReviewResponse = components["schemas"]["SessionReviewResponse"];
export type RejectionIssueCode =
  | "blurry"
  | "bad_exposure"
  | "no_face_detected"
  | "multiple_subjects"
  | "decode_failed";
export type RejectionSummaryItem = {
  code: RejectionIssueCode;
  count: number;
};
export type StatusResponse = components["schemas"]["StatusResponse"] & {
  rejection_summary?: RejectionSummaryItem[] | null;
};
export type SessionStatus = StatusResponse["status"];
export type ResultState = ClassificationResult["result_state"];
export type ProblemDetail = components["schemas"]["ProblemDetail"];
export type ApiErrorCode = ProblemDetail["error_code"];
export type PhotoRejectionReason = components["schemas"]["PhotoRegisterResponse"]["reasons"][number];
