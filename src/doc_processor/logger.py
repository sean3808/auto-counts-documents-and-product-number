"""Log 處理模組"""

from datetime import datetime
from pathlib import Path
from typing import TextIO


class ProcessLogger:
    """處理過程的 Logger，輸出到檔案和控制台"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.log_file: TextIO | None = None
        self.log_path: Path | None = None
        self.success_count = 0
        self.skip_count = 0
        self.fail_count = 0

    def start(self, phase: str) -> None:
        """開始記錄，建立 log 檔案"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = self.output_dir / f"{timestamp}.log"
        self.log_file = open(self.log_path, "w", encoding="utf-8-sig")
        self._reset_counts()

        header = f"""================================================================================
執行時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
執行階段: {phase}
================================================================================
"""
        self._write(header)

    def _reset_counts(self) -> None:
        """重置計數器"""
        self.success_count = 0
        self.skip_count = 0
        self.fail_count = 0

    def _write(self, message: str) -> None:
        """寫入 log 檔案和控制台"""
        print(message, end="")
        if self.log_file:
            self.log_file.write(message)
            self.log_file.flush()

    def info(self, message: str) -> None:
        """記錄一般資訊"""
        self._write(f"[INFO] {message}\n")

    def ok(self, message: str) -> None:
        """記錄成功訊息"""
        self._write(f"[OK] {message}\n")
        self.success_count += 1

    def skip(self, message: str, reason: str) -> None:
        """記錄跳過訊息"""
        self._write(f"[SKIP] {message}\n  - 原因: {reason}\n")
        self.skip_count += 1

    def error(self, message: str, reason: str) -> None:
        """記錄錯誤訊息"""
        self._write(f"[ERROR] {message}\n  - 原因: {reason}\n  - 跳過此項目，不產生輸出\n")
        self.fail_count += 1

    def detail(self, message: str) -> None:
        """記錄細節（縮排）"""
        self._write(f"  - {message}\n")

    def finish(self, phase: str) -> int:
        """結束記錄，回傳退出碼"""
        summary = f"""
--------------------------------------------------------------------------------
{phase} 完成: 成功 {self.success_count}, 跳過 {self.skip_count}, 失敗 {self.fail_count}
================================================================================
"""
        self._write(summary)

        if self.log_file:
            self.log_file.close()
            self.log_file = None

        # 決定退出碼
        if self.fail_count > 0 and self.success_count == 0:
            return 2  # 完全失敗
        elif self.skip_count > 0 or self.fail_count > 0:
            return 1  # 部分失敗
        return 0  # 成功

    def continue_phase(self, phase: str) -> None:
        """繼續記錄下一個階段（用於 all 命令）"""
        self._reset_counts()
        header = f"""
================================================================================
執行階段: {phase}
================================================================================
"""
        self._write(header)
