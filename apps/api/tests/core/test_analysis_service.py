import uuid
from collections.abc import Iterable

import pytest

from color_analysis.core.analysis_service import AnalysisService, _build_rejection_summary
from color_analysis.db.models.analysis_session import AnalysisSession
from color_analysis.db.models.photo_quality import PhotoQuality


class _FakeDb:
    def __init__(self, session_obj: AnalysisSession | None, photo_quality_rows: list[PhotoQuality]) -> None:
        self.session_obj = session_obj
        self.photo_quality_rows = photo_quality_rows

    async def scalar(self, query: object) -> AnalysisSession | None:
        del query
        return self.session_obj

    async def scalars(self, query: object) -> Iterable[PhotoQuality]:
        del query
        return self.photo_quality_rows


def _photo_quality(*, accepted: bool, reasons: str, face_count: int = 1) -> PhotoQuality:
    return PhotoQuality(
        photo_id=uuid.uuid4(),
        accepted=accepted,
        blur_score=50.0,
        exposure_score=0.8,
        face_count=face_count,
        yaw_degrees=0.0,
        pitch_degrees=0.0,
        reasons=reasons,
    )


def test_build_rejection_summary_counts_reason_frequencies() -> None:
    summary = _build_rejection_summary(
        [
            _photo_quality(accepted=False, reasons="blurry, bad_exposure"),
            _photo_quality(accepted=False, reasons="blurry"),
            _photo_quality(accepted=False, reasons="multiple_subjects"),
            _photo_quality(accepted=True, reasons=""),
        ]
    )

    assert [(item.code, item.count) for item in summary] == [
        ("multiple_subjects", 1),
        ("blurry", 2),
        ("bad_exposure", 1),
    ]


@pytest.mark.asyncio
async def test_get_status_includes_rejection_summary_for_retryable_complete_state() -> None:
    session_id = uuid.uuid4()
    service = AnalysisService(
        _FakeDb(
            AnalysisSession(id=session_id, status="complete", result_state="insufficient_photos"),
            [
                _photo_quality(accepted=False, reasons="blurry"),
                _photo_quality(accepted=False, reasons="no_face_detected"),
                _photo_quality(accepted=False, reasons="blurry, bad_exposure"),
            ],
        ),
        redis=None,  # type: ignore[arg-type]
    )

    status = await service.get_status(session_id)

    assert status.status == "complete"
    assert status.result_state == "insufficient_photos"
    assert status.rejection_summary is not None
    assert [(item.code, item.count) for item in status.rejection_summary] == [
        ("no_face_detected", 1),
        ("blurry", 2),
        ("bad_exposure", 1),
    ]


@pytest.mark.asyncio
async def test_get_status_omits_rejection_summary_for_non_retryable_state() -> None:
    session_id = uuid.uuid4()
    service = AnalysisService(
        _FakeDb(
            AnalysisSession(id=session_id, status="complete", result_state="ok"),
            [_photo_quality(accepted=False, reasons="blurry")],
        ),
        redis=None,  # type: ignore[arg-type]
    )

    status = await service.get_status(session_id)

    assert status.status == "complete"
    assert status.result_state == "ok"
    assert status.rejection_summary is None
