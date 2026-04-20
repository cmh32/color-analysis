import json
import sys
from pathlib import Path

from color_analysis.cv.pipeline import run
from color_analysis.cv.types import PhotoInput


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m color_analysis.cv <photo_dir>")

    photo_dir = Path(sys.argv[1])
    photos: list[PhotoInput] = []
    for index, path in enumerate(sorted(photo_dir.glob("*"))):
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".heic", ".heif"}:
            continue
        photos.append(PhotoInput(id=str(index), filename=path.name, payload=path.read_bytes()))

    result = run(photos)
    output = {
        "result_state": result.result_state,
        "scorecard": {
            "warmth": result.scorecard.warmth,
            "value": result.scorecard.value,
            "chroma": result.scorecard.chroma,
            "contrast": result.scorecard.contrast,
        },
        "top_2": list(result.classification.top_2),
        "reliability": {
            "score": result.reliability.score,
            "bucket": result.reliability.bucket,
            "reasons": list(result.reliability.reasons),
        },
        "trace": list(result.trace),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
