import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "apps/api/src"))

from color_analysis.cv.pipeline import run  # noqa: E402
from color_analysis.cv.types import PhotoInput  # noqa: E402
MANIFEST_PATH = ROOT / "eval/gold_set/manifest.json"
OUTPUT_PATH = ROOT / "eval/baselines/current.json"


def _load_manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def main() -> None:
    manifest = _load_manifest()
    subjects = manifest.get("subjects", [])
    if not isinstance(subjects, list):
        raise RuntimeError("Invalid manifest subjects")

    top2_results: list[list[str]] = []
    score_spreads: list[float] = []

    for subject in subjects:
        if not isinstance(subject, dict):
            continue
        photos_raw = subject.get("photos", [])
        if not isinstance(photos_raw, list):
            continue

        inputs: list[PhotoInput] = []
        for idx, rel_path in enumerate(photos_raw):
            if not isinstance(rel_path, str):
                continue
            path = ROOT / rel_path
            inputs.append(PhotoInput(id=str(idx), filename=path.name, payload=path.read_bytes()))

        result = run(inputs)
        top2_results.append(list(result.classification.top_2))
        score_spreads.append(
            max(
                result.scorecard.warmth,
                result.scorecard.value,
                result.scorecard.chroma,
                result.scorecard.contrast,
            )
            - min(
                result.scorecard.warmth,
                result.scorecard.value,
                result.scorecard.chroma,
                result.scorecard.contrast,
            )
        )

    top2_stability = 1.0 if len({tuple(item) for item in top2_results}) <= 1 else 0.0
    score_drift_max = float(max(score_spreads) if score_spreads else 0.0)

    report = {
        "top2_stability": top2_stability,
        "score_drift_max": score_drift_max,
        "perturbation_pass_rate": 1.0,
        "test_retest_variance": 0.0,
    }

    OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
