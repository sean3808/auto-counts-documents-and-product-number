"""pytest 共用 fixtures"""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """測試 fixtures 目錄"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """臨時輸出目錄"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir
