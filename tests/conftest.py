import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.fifa_pipeline.transform import build_model  # noqa: E402


@pytest.fixture(scope="session")
def model():
    return build_model()
