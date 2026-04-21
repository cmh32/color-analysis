import os
import uuid
from io import BytesIO
from collections.abc import Iterable
from contextlib import asynccontextmanager

import pytest
from PIL import Image

from color_analysis.cv.types import Classification as CvClassification
from color_analysis.cv.types import PipelineResult, QualityReport, Reliability, Scorecard
from color_analysis.db.models.analysis_session import AnalysisSession
from color_analysis.db.models.photo import Photo
from color_analysis.db.models.photo_quality import PhotoQuality
from color_analysis.workers.analyze import _build_thumbnail, _run, run_analysis


class _FakeR2:
    def __init__(self) -> None:
        self.thumbnail_keys: list[str] = []
        self.fail_keys: set[str] = set()

    def get_object_bytes(self, key: str) -> bytes:
        if key in self.fail_keys:
            raise RuntimeError("storage read failed")
        image = Image.new("RGB", (640, 480), color=(120, 160, 200))
        buff = BytesIO()
        image.save(buff, format="JPEG")
        return buff.getvalue()

    def put_object_bytes(self, key: str, payload: bytes, content_type: str = "application/octet-stream") -> None:
        del payload, content_type
        self.thumbnail_keys.append(key)


class _FakeSession:
    def __init__(self, session_obj: AnalysisSession, photo_rows: list[Photo]) -> None:
        self.session_obj = session_obj
        self.photo_rows = photo_rows
        self.added: list[object] = []
        self.rollback_called = False

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb

    async def get(self, model: type, key: uuid.UUID) -> AnalysisSession | None:
        del model
        return self.session_obj if self.session_obj.id == key else None

    async def scalars(self, query: object) -> Iterable[Photo]:
        del query
        return self.photo_rows

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        self.rollback_called = True


@pytest.mark.asyncio
async def test_worker_persists_face_count(monkeypatch) -> None:
    session_id = uuid.uuid4()
    photo_id = uuid.uuid4()
    session_obj = AnalysisSession(id=session_id, status="running")
    photo = Photo(
        id=photo_id,
        session_id=session_id,
        storage_key="sessions/test/photos/photo.jpg",
        filename="photo.jpg",
        mime_type="image/jpeg",
        size_bytes=123,
    )
    fake_db = _FakeSession(session_obj, [photo])
    fake_r2 = _FakeR2()

    @asynccontextmanager
    async def fake_session_local():
        yield fake_db

    def fake_run(inputs: Iterable) -> PipelineResult:
        list(inputs)
        return PipelineResult(
            result_state="multiple_subjects",
            scorecard=Scorecard(warmth=0.0, value=0.0, chroma=0.0, contrast=0.0),
            classification=CvClassification(
                top_2=("Autumn", "Spring"),
                probabilities={"Spring": 0.25, "Summer": 0.25, "Autumn": 0.3, "Winter": 0.2},
                margin=0.05,
            ),
            reliability=Reliability(score=0.4, bucket="Low", reasons=("quality=0.4",)),
            trace=("decode+quality", "quality:multiple_subjects"),
            quality_reports={
                str(photo_id): QualityReport(
                    photo_id=str(photo_id),
                    accepted=False,
                    blur_score=82.0,
                    exposure_score=0.8,
                    face_count=2,
                    yaw_degrees=0.0,
                    pitch_degrees=0.0,
                    reasons=("multiple_subjects",),
                )
            },
            per_photo_features=[],
            aggregated_features={},
        )

    monkeypatch.setattr("color_analysis.workers.analyze.SessionLocal", fake_session_local)
    monkeypatch.setattr("color_analysis.workers.analyze._r2", fake_r2)
    monkeypatch.setattr("color_analysis.workers.analyze.run", fake_run)

    await _run(str(session_id))

    photo_quality_rows = [obj for obj in fake_db.added if isinstance(obj, PhotoQuality)]
    assert len(photo_quality_rows) == 1
    assert photo_quality_rows[0].photo_id == photo_id
    assert photo_quality_rows[0].face_count == 2
    assert photo_quality_rows[0].reasons == "multiple_subjects"
    assert session_obj.status == "complete"
    assert session_obj.result_state == "multiple_subjects"
    assert fake_r2.thumbnail_keys == [f"sessions/{session_id}/thumbnails/{photo_id}.jpg"]


@pytest.mark.asyncio
async def test_worker_records_storage_read_failures_as_decode_failed(monkeypatch) -> None:
    session_id = uuid.uuid4()
    good_photo_id = uuid.uuid4()
    bad_photo_id = uuid.uuid4()
    session_obj = AnalysisSession(id=session_id, status="running")
    good_photo = Photo(
        id=good_photo_id,
        session_id=session_id,
        storage_key="sessions/test/photos/good.jpg",
        filename="good.jpg",
        mime_type="image/jpeg",
        size_bytes=123,
    )
    bad_photo = Photo(
        id=bad_photo_id,
        session_id=session_id,
        storage_key="sessions/test/photos/bad.jpg",
        filename="bad.jpg",
        mime_type="image/jpeg",
        size_bytes=123,
    )
    fake_db = _FakeSession(session_obj, [good_photo, bad_photo])
    fake_r2 = _FakeR2()
    fake_r2.fail_keys.add(bad_photo.storage_key)

    @asynccontextmanager
    async def fake_session_local():
        yield fake_db

    def fake_run(inputs: Iterable) -> PipelineResult:
        input_ids = [item.id for item in inputs]
        assert input_ids == [str(good_photo_id)]
        return PipelineResult(
            result_state="insufficient_photos",
            scorecard=Scorecard(warmth=0.0, value=0.0, chroma=0.0, contrast=0.0),
            classification=CvClassification(
                top_2=("Autumn", "Spring"),
                probabilities={"Spring": 0.25, "Summer": 0.25, "Autumn": 0.3, "Winter": 0.2},
                margin=0.05,
            ),
            reliability=Reliability(score=0.4, bucket="Low", reasons=("quality=0.4",)),
            trace=("decode+quality",),
            quality_reports={
                str(good_photo_id): QualityReport(
                    photo_id=str(good_photo_id),
                    accepted=False,
                    blur_score=82.0,
                    exposure_score=0.8,
                    face_count=1,
                    yaw_degrees=0.0,
                    pitch_degrees=0.0,
                    reasons=("blurry",),
                )
            },
            per_photo_features=[],
            aggregated_features={},
        )

    monkeypatch.setattr("color_analysis.workers.analyze.SessionLocal", fake_session_local)
    monkeypatch.setattr("color_analysis.workers.analyze._r2", fake_r2)
    monkeypatch.setattr("color_analysis.workers.analyze.run", fake_run)

    await _run(str(session_id))

    photo_quality_rows = [obj for obj in fake_db.added if isinstance(obj, PhotoQuality)]
    quality_by_photo_id = {row.photo_id: row for row in photo_quality_rows}
    assert len(photo_quality_rows) == 2
    assert quality_by_photo_id[good_photo_id].reasons == "blurry"
    assert quality_by_photo_id[bad_photo_id].reasons == "decode_failed"
    assert quality_by_photo_id[bad_photo_id].accepted is False
    assert session_obj.status == "complete"
    assert session_obj.result_state == "insufficient_photos"
    assert fake_r2.thumbnail_keys == [f"sessions/{session_id}/thumbnails/{good_photo_id}.jpg"]


def test_build_thumbnail_returns_real_jpeg_bytes() -> None:
    source = Image.new("RGB", (400, 300), color=(50, 100, 150))
    buff = BytesIO()
    source.save(buff, format="JPEG")

    thumbnail = _build_thumbnail(buff.getvalue())
    rendered = Image.open(BytesIO(thumbnail))

    assert rendered.format == "JPEG"
    assert rendered.size == (256, 256)


@pytest.mark.skipif(os.getenv("COLOR_ANALYSIS_RUN_WORKER_TESTS") != "1", reason="requires db and storage")
def test_worker_executes() -> None:
    run_analysis("00000000-0000-0000-0000-000000000000")
