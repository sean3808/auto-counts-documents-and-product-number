"""phase1 模組測試"""

from pathlib import Path

import pytest

from doc_processor.logger import ProcessLogger
from doc_processor.phase1 import run_phase1


class TestRunPhase1:
    """Phase 1 整合測試"""

    def test_merge_documents(self, fixtures_dir: Path, temp_output_dir: Path):
        """測試 PDF 合併"""
        logger = ProcessLogger(temp_output_dir)

        exit_code = run_phase1(fixtures_dir, temp_output_dir, logger)

        # 應該成功
        assert exit_code == 0

        # 檢查輸出檔案
        output_files = list(temp_output_dir.glob("*.pdf"))
        assert len(output_files) == 1

        # 檢查檔名格式
        output_name = output_files[0].name
        assert "1011412050003" in output_name
        assert "YC016" in output_name

    def test_empty_input(self, tmp_path: Path, temp_output_dir: Path):
        """測試空的 input 資料夾"""
        empty_input = tmp_path / "empty_input"
        empty_input.mkdir()

        logger = ProcessLogger(temp_output_dir)
        exit_code = run_phase1(empty_input, temp_output_dir, logger)

        # 沒有檔案應該回傳成功（沒有失敗）
        assert exit_code == 0
