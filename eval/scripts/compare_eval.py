import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = ROOT / "eval/baselines/latest.json"
CURRENT_PATH = ROOT / "eval/baselines/current.json"


def main() -> None:
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    current = json.loads(CURRENT_PATH.read_text(encoding="utf-8"))

    failures: list[str] = []

    top2_drop = baseline["top2_stability"] - current["top2_stability"]
    if top2_drop > 0.02:
        failures.append(f"top2_stability dropped by {top2_drop:.3f}")

    drift_increase = current["score_drift_max"] - baseline["score_drift_max"]
    if drift_increase > 0.1:
        failures.append(f"score_drift_max increased by {drift_increase:.3f}")

    if failures:
        raise SystemExit("Eval regression: " + "; ".join(failures))

    print("Eval regression check passed")


if __name__ == "__main__":
    main()
