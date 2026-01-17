"""Log 處理模組"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TextIO

_SEPARATOR = "=" * 80
_SEPARATOR_THIN = "-" * 80


@dataclass
class MissingItem:
    """缺漏項目資訊"""

    phase: str
    item_type: str
    description: str
    suggestion: str


class ProcessLogger:
    """處理過程的 Logger，輸出到檔案和控制台"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.log_file: TextIO | None = None
        self.log_path: Path | None = None
        self.success_count = 0
        self.skip_count = 0
        self.fail_count = 0
        # 追蹤所有缺漏項目（跨階段累計）
        self._missing_items: list[MissingItem] = []
        # 追蹤各階段統計
        self._phase_stats: list[tuple[str, int, int, int]] = []
        # 當前階段名稱
        self._current_phase: str = ""

    def start(self, phase: str) -> None:
        """開始記錄，建立 log 檔案"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = self.output_dir / f"{timestamp}.log"
        self.log_file = open(self.log_path, "w", encoding="utf-8-sig")
        self._reset_counts()
        self._current_phase = phase

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"""{_SEPARATOR}
執行時間: {now}
執行階段: {phase}
{_SEPARATOR}
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

    def skip(
        self,
        message: str,
        reason: str,
        suggestion: str | None = None,
    ) -> None:
        """記錄跳過訊息"""
        self._write(f"[SKIP] {message}\n  - 原因: {reason}\n")
        self.skip_count += 1
        # 記錄缺漏項目
        if suggestion:
            self._missing_items.append(
                MissingItem(
                    phase=self._current_phase,
                    item_type="跳過",
                    description=f"{message} - {reason}",
                    suggestion=suggestion,
                )
            )

    def error(
        self,
        message: str,
        reason: str,
        suggestion: str | None = None,
    ) -> None:
        """記錄錯誤訊息"""
        self._write(f"[ERROR] {message}\n  - 原因: {reason}\n  - 跳過此項目，不產生輸出\n")
        self.fail_count += 1
        # 記錄缺漏項目
        if suggestion:
            self._missing_items.append(
                MissingItem(
                    phase=self._current_phase,
                    item_type="錯誤",
                    description=f"{message} - {reason}",
                    suggestion=suggestion,
                )
            )

    def detail(self, message: str) -> None:
        """記錄細節（縮排）"""
        self._write(f"  - {message}\n")

    def finish(self, phase: str) -> int:
        """結束記錄，回傳退出碼"""
        # 儲存本階段統計
        self._phase_stats.append(
            (phase, self.success_count, self.skip_count, self.fail_count)
        )

        counts = f"成功 {self.success_count}, 跳過 {self.skip_count}, 失敗 {self.fail_count}"
        summary = f"\n{_SEPARATOR_THIN}\n{phase} 完成: {counts}\n{_SEPARATOR}\n"
        self._write(summary)

        if self.log_file:
            self.log_file.close()
            self.log_file = None

        if self.fail_count > 0 and self.success_count == 0:
            return 2  # 完全失敗
        if self.skip_count > 0 or self.fail_count > 0:
            return 1  # 部分失敗
        return 0  # 成功

    def continue_phase(self, phase: str) -> None:
        """繼續記錄下一個階段（用於 all 命令）"""
        # 若檔案已被 finish() 關閉，重新以 append 模式開啟
        if self.log_file is None and self.log_path:
            self.log_file = open(self.log_path, "a", encoding="utf-8-sig")

        self._reset_counts()
        self._current_phase = phase
        header = f"\n{_SEPARATOR}\n執行階段: {phase}\n{_SEPARATOR}\n"
        self._write(header)

    def add_missing_item(
        self,
        item_type: str,
        description: str,
        suggestion: str,
    ) -> None:
        """手動新增缺漏項目（不影響計數）"""
        self._missing_items.append(
            MissingItem(
                phase=self._current_phase,
                item_type=item_type,
                description=description,
                suggestion=suggestion,
            )
        )

    def write_summary(self) -> None:
        """寫入最終摘要（Summary/Conclusion）"""
        # 重新開啟檔案（如果已關閉）
        if self.log_file is None and self.log_path:
            self.log_file = open(self.log_path, "a", encoding="utf-8-sig")

        self._write(f"\n{_SEPARATOR}\n")
        self._write("最終摘要 (Summary)\n")
        self._write(f"{_SEPARATOR}\n\n")

        # 各階段統計
        if self._phase_stats:
            self._write("【各階段執行結果】\n")
            total_success = 0
            total_skip = 0
            total_fail = 0
            for phase_name, success, skip, fail in self._phase_stats:
                self._write(f"  - {phase_name}: 成功 {success}, 跳過 {skip}, 失敗 {fail}\n")
                total_success += success
                total_skip += skip
                total_fail += fail
            self._write(f"  - 總計: 成功 {total_success}, 跳過 {total_skip}, 失敗 {total_fail}\n")
            self._write("\n")

        # 缺漏項目與建議
        if self._missing_items:
            self._write("【需補齊的文件/檔案】\n")
            for item in self._missing_items:
                self._write(f"  [{item.phase}] {item.description}\n")
                self._write(f"    -> 建議: {item.suggestion}\n")
            self._write("\n")
        else:
            self._write("【需補齊的文件/檔案】\n")
            self._write("  未偵測到需補齊的文件/檔案\n\n")

        # 下一步行動
        self._write("【下一步行動】\n")
        if self._missing_items:
            self._write("  請依照上述建議補齊缺漏的文件後，重新執行處理流程。\n")
        else:
            total_fail = sum(fail for _, _, _, fail in self._phase_stats)
            total_skip = sum(skip for _, _, skip, _ in self._phase_stats)
            if total_fail == 0 and total_skip == 0:
                self._write("  所有處理已成功完成，無需進一步動作。\n")
            else:
                self._write("  部分項目已跳過或失敗，請檢視上方 log 以確認詳情。\n")

        self._write(f"\n{_SEPARATOR}\n")

        # 關閉檔案
        if self.log_file:
            self.log_file.close()
            self.log_file = None
