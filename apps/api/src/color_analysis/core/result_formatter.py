from color_analysis.db.models.classification import Classification
from color_analysis.schemas.analysis import AnalysisResult, Reliability, Scorecard


def format_result(classification: Classification) -> AnalysisResult:
    scorecard = Scorecard(**classification.scorecard)
    reliability = Reliability(
        score=classification.reliability,
        bucket=classification.reliability_bucket,
        reasons=["Based on photo quality, consistency, and classifier margin"],
    )

    return AnalysisResult(
        session_id=str(classification.session_id),
        top_2_seasons=(classification.primary_season, classification.secondary_season),
        scorecard=scorecard,
        reliability=reliability,
        result_state=classification.result_state,
        trace=[
            "decode -> quality -> landmarks -> regions -> white_balance",
            "features -> aggregate -> scorecard -> classify",
        ],
    )
