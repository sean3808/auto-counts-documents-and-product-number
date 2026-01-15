"""CLI 入口模組"""

import argparse
import sys
from pathlib import Path

from .logger import ProcessLogger
from .phase1 import run_phase1
from .phase2 import run_phase2


def main() -> int:
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog="doc_processor",
        description="採購單關聯單據重組與單據明細產生器",
    )
    parser.add_argument(
        "command",
        choices=["phase1", "phase2", "all"],
        help="執行的階段：phase1=合併PDF, phase2=產生Excel, all=依序執行",
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

    args = parser.parse_args()

    # 確保輸出資料夾存在
    args.output.mkdir(parents=True, exist_ok=True)

    # 建立 logger
    logger = ProcessLogger(args.output)

    # 執行指定的階段
    if args.command == "phase1":
        return run_phase1(args.input, args.output, logger)

    elif args.command == "phase2":
        return run_phase2(args.output, args.template, logger)

    elif args.command == "all":
        # 依序執行 Phase 1 + Phase 2
        exit_code_1 = run_phase1(args.input, args.output, logger)

        # Phase 1 完全失敗時不執行 Phase 2
        if exit_code_1 == 2:
            return exit_code_1

        exit_code_2 = run_phase2(
            args.output, args.template, logger, is_continuation=True
        )

        # 回傳較嚴重的退出碼
        return max(exit_code_1, exit_code_2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
