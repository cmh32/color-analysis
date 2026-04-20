import os

import pytest

from color_analysis.workers.analyze import run_analysis


@pytest.mark.skipif(os.getenv("COLOR_ANALYSIS_RUN_WORKER_TESTS") != "1", reason="requires db and storage")
def test_worker_executes() -> None:
    run_analysis("00000000-0000-0000-0000-000000000000")
