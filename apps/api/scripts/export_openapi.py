import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "src"))

from color_analysis.main import app


def main() -> None:
    destination = ROOT / "openapi.json"
    destination.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
