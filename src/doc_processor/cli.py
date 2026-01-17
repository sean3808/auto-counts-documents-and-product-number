"""CLI 入口模組"""

import argparse
import sys
from pathlib import Path

from .logger import ProcessLogger
from .phase0 import run_phase0
from .phase1 import run_phase1
from .phase2 import run_phase2

# 預設暫存資料夾
DEFAULT_TEMP_DIR = Path("./temp/stamped")


def main() -> int:
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog="doc_processor",
        description="採購單關聯單據重組與單據明細產生器",
    )
    parser.add_argument(
        "command",
        choices=["phase0", "phase1", "phase2", "all"],
        help="執行的階段：phase0=蓋章, phase1=合併PDF, phase2=產生Excel, all=依序執行",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("./input"),
        help="輸入資料夾路徑（預設: ./input）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./output"),
        help="輸出資料夾路徑（預設: ./output）",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=Path("./template.xlsx"),
        help="Excel 模板路徑（預設: ./template.xlsx）",
    )
    parser.add_argument(
        "--stamps",
        type=Path,
        default=Path("./印章/removebg"),
        help="印章資料夾路徑（預設: ./印章/removebg）",
    )

    args = parser.parse_args()

    # 確保輸出資料夾存在
    args.output.mkdir(parents=True, exist_ok=True)

    # 建立 logger
    logger = ProcessLogger(args.output)

    # 執行指定的階段
    if args.command == "phase0":
        result = run_phase0(args.input, DEFAULT_TEMP_DIR, args.stamps, logger)
        logger.write_summary()
        _print_log_path(logger)
        return result

    elif args.command == "phase1":
        # Phase 1 單獨執行時，從 input 讀取（向後兼容）
        result = run_phase1(args.input, args.output, logger)
        logger.write_summary()
        _print_log_path(logger)
        return result

    elif args.command == "phase2":
        result = run_phase2(args.output, args.template, logger)
        logger.write_summary()
        _print_log_path(logger)
        return result

    elif args.command == "all":
        # 依序執行 Phase 0 + Phase 1 + Phase 2
        exit_code_0 = run_phase0(args.input, DEFAULT_TEMP_DIR, args.stamps, logger)

        if exit_code_0 == 2:
            logger.write_summary()
            _print_log_path(logger)
            return exit_code_0

        # Phase 1 從 temp/stamped 讀取
        exit_code_1 = run_phase1(
            DEFAULT_TEMP_DIR, args.output, logger, is_continuation=True
        )

        if exit_code_1 == 2:
            logger.write_summary()
            _print_log_path(logger)
            return max(exit_code_0, exit_code_1)

        exit_code_2 = run_phase2(
            args.output, args.template, logger, is_continuation=True
        )

        logger.write_summary()
        _print_log_path(logger)
        return max(exit_code_0, exit_code_1, exit_code_2)

    return 0


def _print_log_path(logger: ProcessLogger) -> None:
    """輸出 log 檔案路徑供 run.ps1 捕獲"""
    if logger.log_path:
        # 使用特殊標記，方便 run.ps1 解析
        print(f"LOG_FILE_PATH:{logger.log_path.resolve()}")


if __name__ == "__main__":
    sys.exit(main())
