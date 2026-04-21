import uuid
from collections.abc import Iterable

import pytest

from color_analysis.core.analysis_service import AnalysisService, _build_rejection_summary
from color_analysis.db.models.analysis_session import AnalysisSession
from color_analysis.db.models.photo import Photo
from color_analysis.db.models.photo_quality import PhotoQuality


class _FakeDb:
    def __init__(
        self,
        session_obj: AnalysisSession | None,
        photo_quality_rows: list[PhotoQuality],
        review_rows: list[tuple[Photo, PhotoQuality]] | None = None,
    ) -> None:
        self.session_obj = session_obj
        self.photo_quality_rows = photo_quality_rows
        self.review_rows = review_rows or []

    async def scalar(self, query: object) -> AnalysisSession | None:
        del query
        return self.session_obj

    async def scalars(self, query: object) -> Iterable[PhotoQuality]:
        del query
        return self.photo_quality_rows

    async def execute(self, query: object):
        del query

        class _Result:
            def __init__(self, rows: list[tuple[Photo, PhotoQuality]]) -> None:
                self._rows = rows

            def all(self) -> list[tuple[Photo, PhotoQuality]]:
                return self._rows

        return _Result(self.review_rows)


class _FakeR2:
    def get_presigned_get_url(self, key: str, expires_in_seconds: int = 3600) -> str:
        return f"https://example.test/{key}?expires={expires_in_seconds}"


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


@pytest.mark.asyncio
async def test_get_review_returns_rejected_photos_with_preview_urls() -> None:
    session_id = uuid.uuid4()
    photo_id = uuid.uuid4()
    session = AnalysisSession(id=session_id, status="complete", result_state="insufficient_photos")
    photo = Photo(
        id=photo_id,
        session_id=session_id,
        storage_key="sessions/test/photos/photo.jpg",
        filename="photo.jpg",
        mime_type="image/jpeg",
        size_bytes=123,
    )
    quality = _photo_quality(accepted=False, reasons="blurry, bad_exposure")
    quality.photo_id = photo_id
    service = AnalysisService(
        _FakeDb(session, [], [(photo, quality)]),
        redis=None,  # type: ignore[arg-type]
        r2=_FakeR2(),  # type: ignore[arg-type]
    )

    review = await service.get_review(session)

    assert len(review.rejected_photos) == 1
    assert review.rejected_photos[0].photo_id == str(photo_id)
    assert review.rejected_photos[0].filename == "photo.jpg"
    assert review.rejected_photos[0].reasons == ["blurry", "bad_exposure"]
    assert review.rejected_photos[0].preview_url.startswith(
        f"https://example.test/sessions/{session_id}/thumbnails/{photo_id}.jpg"
    )


@pytest.mark.asyncio
async def test_get_review_uses_original_photo_for_decode_failed_preview() -> None:
    session_id = uuid.uuid4()
    photo_id = uuid.uuid4()
    session = AnalysisSession(id=session_id, status="complete", result_state="insufficient_photos")
    photo = Photo(
        id=photo_id,
        session_id=session_id,
        storage_key="sessions/test/photos/photo.jpg",
        filename="photo.jpg",
        mime_type="image/jpeg",
        size_bytes=123,
    )
    quality = _photo_quality(accepted=False, reasons="decode_failed")
    quality.photo_id = photo_id
    service = AnalysisService(
        _FakeDb(session, [], [(photo, quality)]),
        redis=None,  # type: ignore[arg-type]
        r2=_FakeR2(),  # type: ignore[arg-type]
    )

    review = await service.get_review(session)

    assert len(review.rejected_photos) == 1
    assert review.rejected_photos[0].preview_url.startswith(
        "https://example.test/sessions/test/photos/photo.jpg"
    )
