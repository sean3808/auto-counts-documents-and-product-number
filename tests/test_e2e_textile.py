"""紡織類樣本端到端全流程驗證（Phase 0 ~ Phase 2）與回歸測試套件

驗收 Issue #4 & Issue #9：
1. 端到端執行 Phase 0，驗證紡織類四類單據產出均符合預期對照印章配置。
2. 以進貨驗收單_2_NEW.pdf 為黃金樣本，精確校驗 3 個印章（進料檢驗章、莊宛恬、雅萍）之種類、尺寸與座標。
3. 驗證 Phase 1 產出合併 PDF 命名為 1011506080001-GL012-金利多企.pdf（ERP 原生文字層簡稱截斷），且順序為 進貨單 > 進貨驗收單 > 採購單 > 請購單。
4. 驗證 Phase 2 正確產出 Excel 單據明細表，且張數（1 張，依單據號碼計）與支數（1 支）正確填入 B3 與 C3。
5. 執行 uv run python -m doc_processor all CLI 全流程，驗證 temp 與 output 目錄產出結果符合預期。
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import fitz
import pytest
from openpyxl import load_workbook

from doc_processor.logger import ProcessLogger
from doc_processor.phase0 import run_phase0
from doc_processor.phase1 import run_phase1
from doc_processor.phase2 import run_phase2

ISSUE_CLEAN_DIR = Path("issue/乾淨對照")
ISSUE_EXPECTED_DIR = Path("issue/預期對照")
STAMPS_DIR = Path("印章/removebg")
TEMPLATE_PATH = Path("template.xlsx")

pytestmark = pytest.mark.skipif(
    not ISSUE_CLEAN_DIR.exists() or not ISSUE_EXPECTED_DIR.exists() or not STAMPS_DIR.exists(),
    reason="需要 issue/ 測試樣本與印章圖檔",
)


def _rect_center(rect: fitz.Rect) -> tuple[float, float]:
    """計算矩形中心點 (center_x, center_y)"""
    return ((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)


@pytest.fixture
def textile_env(tmp_path: Path):
    """建立端到端測試所需的輸入、暫存與輸出目錄結構"""
    input_dir = tmp_path / "input"
    stamped_dir = tmp_path / "stamped"
    output_dir = tmp_path / "output"

    input_dir.mkdir(parents=True)
    stamped_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    # 複製乾淨對照樣本至 input_dir
    for pdf_file in ISSUE_CLEAN_DIR.glob("*.pdf"):
        shutil.copy(pdf_file, input_dir / pdf_file.name)

    return {
        "input_dir": input_dir,
        "stamped_dir": stamped_dir,
        "output_dir": output_dir,
        "stamps_dir": STAMPS_DIR,
        "template_path": TEMPLATE_PATH,
    }


class TestTextileEndToEnd:
    """紡織樣本全流程整合與端到端測試"""

    def test_phase0_textile_stamping_and_alignment(self, textile_env):
        """
        驗收條件 1 & 2：
        - 端到端執行 Phase 0，驗證紡織類四類單據產出均符合預期對照印章配置
        - 比對 Phase 0 產出 PDF 圖片數量與座標中心點，確認在預期公差範圍內
        """
        logger = ProcessLogger(textile_env["output_dir"])
        exit_code = run_phase0(
            textile_env["input_dir"],
            textile_env["stamped_dir"],
            textile_env["stamps_dir"],
            logger,
        )

        assert exit_code == 0, "Phase 0 執行應成功"

        # 對照表：實際檔名 -> 預期檔名
        file_mapping = {
            "採購單~1 1.pdf": "採購單_1.pdf",
            "請購單~2 1.pdf": "請購單_2.pdf",
            "進貨單~2 1.pdf": "進貨單_2.pdf",
            "進貨驗收單~2 1.pdf": "進貨驗收單_2_NEW.pdf",
        }

        for actual_name, expected_name in file_mapping.items():
            actual_path = textile_env["stamped_dir"] / actual_name
            expected_path = ISSUE_EXPECTED_DIR / expected_name

            assert actual_path.exists(), f"Phase 0 產出檔案不存在: {actual_name}"
            assert expected_path.exists(), f"預期對照檔案不存在: {expected_name}"

            act_doc = fitz.open(actual_path)
            exp_doc = fitz.open(expected_path)

            assert len(act_doc) == len(exp_doc) == 1, f"{actual_name} 頁數應為 1 頁"

            act_page = act_doc[0]
            exp_page = exp_doc[0]

            act_images = act_page.get_images()
            exp_images = exp_page.get_images()

            # 驗證圖片數量
            assert len(act_images) == len(exp_images), (
                f"{actual_name} 圖片數量不符：實際 {len(act_images)}, 預期 {len(exp_images)}"
            )

            if actual_name == "進貨驗收單~2 1.pdf":
                # 紡織類進貨驗收單應有 3 個印章：進料檢驗章、莊宛恬倉管章與製單章
                assert len(act_images) == 3, "紡織類進貨驗收單應有 3 個印章"

            # 取得各圖片的顯示矩形並依 x 座標排序
            act_rects = sorted(
                [act_page.get_image_rects(img[0])[0] for img in act_images],
                key=lambda r: r.x0,
            )
            exp_rects = sorted(
                [exp_page.get_image_rects(img[0])[0] for img in exp_images],
                key=lambda r: r.x0,
            )

            for act_rect, exp_rect in zip(act_rects, exp_rects):
                act_center = _rect_center(act_rect)
                exp_center = _rect_center(exp_rect)

                diff_x = abs(act_center[0] - exp_center[0])
                diff_y = abs(act_center[1] - exp_center[1])

                # 進料檢驗章（寬度 > 100 pt）因等比例縮放高為 153 pt（原目標框高 166.7 pt），中心 y 偏移約 6.8 pt，加計 ±3pt 自然化抖動上限約 9.8 pt；個人職章自然化抖動 x∈[-4, +4], y∈[-3, +3]，兩獨立隨機本中心差上限分別為 8.5 pt 與 7.5 pt
                is_inspection = act_rect.width > 100
                max_diff_x = 10.0 if is_inspection else 8.5
                max_diff_y = 10.0 if is_inspection else 7.5

                assert diff_x <= max_diff_x, (
                    f"{actual_name} 印章中心 x 偏移 {diff_x:.2f} pt 超出容許公差"
                )
                assert diff_y <= max_diff_y, (
                    f"{actual_name} 印章中心 y 偏移 {diff_y:.2f} pt 超出容許公差"
                )

                # 尺寸檢查
                if is_inspection:
                    assert abs(act_rect.width - 221.4) <= 4.0, (
                        f"{actual_name} 進料檢驗章寬度應約 221.4 pt"
                    )
                    assert 148.0 <= act_rect.height <= 170.0, (
                        f"{actual_name} 進料檢驗章高度應在 [148, 170] pt 範圍內"
                    )
                else:
                    assert any(
                        abs(act_rect.width - target_w) <= 3.5
                        for target_w in (32.1, 28.0)
                    ), (
                        f"{actual_name} 職章寬度應約 32.1 pt 或 28.0 pt (實際: {act_rect.width:.1f})"
                    )
                    assert any(
                        abs(act_rect.height - target_h) <= 3.5
                        for target_h in (17.3, 17.0)
                    ), (
                        f"{actual_name} 職章高度應約 17.3 pt 或 17.0 pt (實際: {act_rect.height:.1f})"
                    )

            act_doc.close()
            exp_doc.close()

    def test_receiving_three_stamps_golden_sample_alignment(self, textile_env):
        """
        驗收條件 1 & 2 (Issue #9)：
        - 以 `issue/預期對照/進貨驗收單_2_NEW.pdf` 作為黃金樣本校對
        - 精確比對進料檢驗章、莊宛恬倉管章、雅萍製單章 3 個印章之種類、尺寸與座標
        - 驗證自然化位移與公差在規範範圍內
        """
        logger = ProcessLogger(textile_env["output_dir"])
        exit_code = run_phase0(
            textile_env["input_dir"],
            textile_env["stamped_dir"],
            textile_env["stamps_dir"],
            logger,
        )
        assert exit_code == 0

        actual_path = textile_env["stamped_dir"] / "進貨驗收單~2 1.pdf"
        golden_path = ISSUE_EXPECTED_DIR / "進貨驗收單_2_NEW.pdf"

        act_doc = fitz.open(actual_path)
        exp_doc = fitz.open(golden_path)

        try:
            assert len(act_doc) == 1 and len(exp_doc) == 1
            act_page = act_doc[0]
            exp_page = exp_doc[0]

            act_imgs = act_page.get_images()
            exp_imgs = exp_page.get_images()
            assert len(act_imgs) == 3, "實際產出進貨驗收單應有 3 個印章"
            assert len(exp_imgs) == 3, "黃金樣本進貨驗收單應有 3 個印章"

            # 依 x0 座標排序：
            # 1. x0 ~ 40: 進料檢驗章
            # 2. x0 ~ 176: 莊宛恬倉管章
            # 3. x0 ~ 508: 雅萍製單章
            act_rects = sorted(
                [act_page.get_image_rects(img[0])[0] for img in act_imgs],
                key=lambda r: r.x0,
            )
            exp_rects = sorted(
                [exp_page.get_image_rects(img[0])[0] for img in exp_imgs],
                key=lambda r: r.x0,
            )

            # 印章 1：進料檢驗章（紡織進料檢）
            inspection_act, inspection_exp = act_rects[0], exp_rects[0]
            # 基準座標：x=40.5 ± 4, y=270.4 ± 3（含 0.2 pt 浮點數微差裕度）
            assert 36.3 <= inspection_act.x0 <= 44.7, f"進料檢驗章 x0 應在 [36.5, 44.5]，實際 {inspection_act.x0}"
            assert 267.2 <= inspection_act.y0 <= 273.6, f"進料檢驗章 y0 應在 [267.4, 273.4]，實際 {inspection_act.y0}"
            # 尺寸：寬度約 221.4 pt，等比例縮放高度約 153.0 pt（原圖 427x306）
            assert abs(inspection_act.width - 221.4) <= 4.0, f"進料檢驗章寬度應約 221.4 pt，實際 {inspection_act.width}"
            assert 148.0 <= inspection_act.height <= 165.0, f"進料檢驗章高度應在 [148, 165]，實際 {inspection_act.height}"
            # 與黃金樣本中心點距離公差
            act_center_insp = _rect_center(inspection_act)
            exp_center_insp = _rect_center(inspection_exp)
            assert abs(act_center_insp[0] - exp_center_insp[0]) <= 10.0, "進料檢驗章中心 x 與黃金樣本差應 <= 10 pt"
            assert abs(act_center_insp[1] - exp_center_insp[1]) <= 10.0, "進料檢驗章中心 y 與黃金樣本差應 <= 10 pt"

            # 印章 2：紡織類倉管章（莊宛恬）
            warehouse_act, warehouse_exp = act_rects[1], exp_rects[1]
            # 基準座標：x=176.1 ± 4, y=743.3 ± 3（含 0.2 pt 浮點數微差裕度）
            assert 171.9 <= warehouse_act.x0 <= 180.3, f"莊宛恬章 x0 應在 [172.1, 180.1]，實際 {warehouse_act.x0}"
            assert 740.1 <= warehouse_act.y0 <= 746.5, f"莊宛恬章 y0 應在 [740.3, 746.3]，實際 {warehouse_act.y0}"
            # 尺寸：目標 28.0 x 17.0 pt
            assert abs(warehouse_act.width - 28.0) <= 3.5, f"莊宛恬章寬度應約 28.0 pt，實際 {warehouse_act.width}"
            assert abs(warehouse_act.height - 17.0) <= 3.5, f"莊宛恬章高度應約 17.0 pt，實際 {warehouse_act.height}"
            # 與黃金樣本中心點距離公差
            act_center_wh = _rect_center(warehouse_act)
            exp_center_wh = _rect_center(warehouse_exp)
            assert abs(act_center_wh[0] - exp_center_wh[0]) <= 8.5, "莊宛恬章中心 x 與黃金樣本差應 <= 8.5 pt"
            assert abs(act_center_wh[1] - exp_center_wh[1]) <= 7.5, "莊宛恬章中心 y 與黃金樣本差應 <= 7.5 pt"

            # 印章 3：製單章（雅萍）
            creator_act, creator_exp = act_rects[2], exp_rects[2]
            # 基準座標：x=508.2 ± 4, y=743.8 ± 3（含 0.2 pt 浮點數微差裕度）
            assert 504.0 <= creator_act.x0 <= 512.4, f"雅萍章 x0 應在 [504.2, 512.2]，實際 {creator_act.x0}"
            assert 740.6 <= creator_act.y0 <= 747.0, f"雅萍章 y0 應在 [740.8, 746.8]，實際 {creator_act.y0}"
            # 尺寸：目標 32.1 x 17.3 pt
            assert abs(creator_act.width - 32.1) <= 3.5, f"雅萍章寬度應約 32.1 pt，實際 {creator_act.width}"
            assert abs(creator_act.height - 17.3) <= 3.5, f"雅萍章高度應約 17.3 pt，實際 {creator_act.height}"
            # 與黃金樣本中心點距離公差
            act_center_cr = _rect_center(creator_act)
            exp_center_cr = _rect_center(creator_exp)
            assert abs(act_center_cr[0] - exp_center_cr[0]) <= 8.5, "雅萍章中心 x 與黃金樣本差應 <= 8.5 pt"
            assert abs(act_center_cr[1] - exp_center_cr[1]) <= 7.5, "雅萍章中心 y 與黃金樣本差應 <= 7.5 pt"

            # 自然化參數規格驗證（旋轉角 ±3°、位移 x: ±4pt、y: ±3pt）
            from doc_processor.phase0 import (
                OFFSET_X_MAX,
                OFFSET_X_MIN,
                OFFSET_Y_MAX,
                OFFSET_Y_MIN,
                ROTATION_MAX_DEGREES,
                ROTATION_MIN_DEGREES,
            )

            assert ROTATION_MIN_DEGREES == -3 and ROTATION_MAX_DEGREES == 3
            assert OFFSET_X_MIN == -4 and OFFSET_X_MAX == 4
            assert OFFSET_Y_MIN == -3 and OFFSET_Y_MAX == 3
        finally:
            act_doc.close()
            exp_doc.close()

    def test_phase1_textile_merging(self, textile_env):
        """
        驗收條件 3：
        - 驗證 Phase 1 產出合併 PDF 命名為 1011506080001-GL012-金利多企.pdf（ERP 原生文字層簡稱截斷）
        - 單據合併順序符合「進貨單 > 進貨驗收單 > 採購單 > 請購單」
        """
        logger = ProcessLogger(textile_env["output_dir"])

        # 先執行 Phase 0
        rc0 = run_phase0(
            textile_env["input_dir"],
            textile_env["stamped_dir"],
            textile_env["stamps_dir"],
            logger,
        )
        assert rc0 == 0

        # 執行 Phase 1
        rc1 = run_phase1(
            textile_env["stamped_dir"],
            textile_env["output_dir"],
            logger,
            is_continuation=True,
        )
        assert rc1 == 0, "Phase 1 執行應成功"

        # 依規格從進貨驗收單原生文字層抽取「供商簡稱」，因 ERP 欄位寬度限制，驗收單內文為「金利多企」
        expected_filename = "1011506080001-GL012-金利多企.pdf"
        merged_pdf = textile_env["output_dir"] / expected_filename
        assert merged_pdf.exists(), f"合併 PDF 檔案應存在且命名為 {expected_filename}"

        # 驗證頁數與合併順序
        doc = fitz.open(merged_pdf)
        assert len(doc) == 4, "紡織類單據合併後應為 4 頁"

        # 依序驗證每頁單別
        page_0_text = doc[0].get_text()
        page_1_text = doc[1].get_text()
        page_2_text = doc[2].get_text()
        page_3_text = doc[3].get_text()

        # 第 0 頁：進貨單
        assert "進貨單" in page_0_text and "單據號碼:" in page_0_text, "第 1 頁應為進貨單"
        # 第 1 頁：進貨驗收單
        assert "進貨驗收單" in page_1_text and "驗收單號：" in page_1_text, "第 2 頁應為進貨驗收單"
        # 第 2 頁：採購單
        assert "採購單" in page_2_text and "採購單號:" in page_2_text, "第 3 頁應為採購單"
        # 第 3 頁：請購單
        assert "請購單" in page_3_text and "請購單號:" in page_3_text, "第 4 頁應為請購單"

        doc.close()

    def test_phase2_textile_excel_generation(self, textile_env):
        """
        驗收條件 4：
        - 驗證 Phase 2 正確產出 Excel 單據明細表
        - 張數（1 張，依「單據號碼」次數抽取填入進貨單張數）與支數（1 支）正確填入 C3 與 B3
        - 採購單號正確填入 G2
        """
        logger = ProcessLogger(textile_env["output_dir"])

        # 執行 Phase 0 & Phase 1
        run_phase0(
            textile_env["input_dir"],
            textile_env["stamped_dir"],
            textile_env["stamps_dir"],
            logger,
        )
        run_phase1(
            textile_env["stamped_dir"],
            textile_env["output_dir"],
            logger,
            is_continuation=True,
        )

        # 執行 Phase 2
        rc2 = run_phase2(
            textile_env["output_dir"],
            textile_env["template_path"],
            logger,
            is_continuation=True,
        )
        assert rc2 == 0, "Phase 2 執行應成功"

        expected_excel = textile_env["output_dir"] / "1011506080001-單據明細.xlsx"
        assert expected_excel.exists(), f"Excel 明細檔案應存在: {expected_excel.name}"

        wb = load_workbook(expected_excel)
        ws = wb.active

        # B3 為支數 (1 支: 0001 JAC胚布)
        assert ws["B3"].value == 1, "B3 支數應為 1"
        # C3 為張數 (1 張進貨單，依內文中「單據號碼」次數計算)
        assert ws["C3"].value == 1, "C3 張數應為 1"
        # G2 為採購單號
        assert ws["G2"].value == "1011506080001", "G2 採購單號應為 1011506080001"

        wb.close()

    def test_full_pipeline_textile_end_to_end(self, textile_env):
        """
        驗收條件 5：
        - 全管線端到端串接驗證（Phase 0 -> Phase 1 -> Phase 2）
        - 驗證完整產物鏈與執行日誌
        """
        logger = ProcessLogger(textile_env["output_dir"])

        # 階段 0
        rc0 = run_phase0(
            textile_env["input_dir"],
            textile_env["stamped_dir"],
            textile_env["stamps_dir"],
            logger,
        )
        assert rc0 == 0

        # 階段 1
        rc1 = run_phase1(
            textile_env["stamped_dir"],
            textile_env["output_dir"],
            logger,
            is_continuation=True,
        )
        assert rc1 == 0

        # 階段 2
        rc2 = run_phase2(
            textile_env["output_dir"],
            textile_env["template_path"],
            logger,
            is_continuation=True,
        )
        assert rc2 == 0

        # 寫入最終日誌總結
        logger.write_summary()

        # 驗證最終輸出成品
        output_files = list(textile_env["output_dir"].iterdir())
        pdf_outputs = [f for f in output_files if f.suffix == ".pdf"]
        excel_outputs = [f for f in output_files if f.suffix == ".xlsx"]
        log_outputs = [f for f in output_files if f.suffix == ".log"]

        assert len(pdf_outputs) == 1, "成品應包含 1 份合併 PDF"
        assert pdf_outputs[0].name == "1011506080001-GL012-金利多企.pdf"

        assert len(excel_outputs) == 1, "成品應包含 1 份明細 Excel"
        assert excel_outputs[0].name == "1011506080001-單據明細.xlsx"

        assert len(log_outputs) == 1, "應產出執行日誌"
        log_content = log_outputs[0].read_text(encoding="utf-8")
        assert "全部成功" in log_content or "成功 1" in log_content

    def test_cli_doc_processor_all_execution(self, textile_env):
        """
        驗收條件 3 & 4 (Issue #9)：
        - 執行 uv run python -m doc_processor all 全流程
        - 驗證 temp/stamped 與 output 目錄產出結果符合預期
        - 驗證日誌與退出碼為 0
        """
        uv_bin = shutil.which("uv")
        cmd_prefix = [uv_bin, "run", "python"] if uv_bin else [sys.executable]
        cmd = cmd_prefix + [
            "-m",
            "doc_processor",
            "all",
            "--input",
            str(textile_env["input_dir"]),
            "--output",
            str(textile_env["output_dir"]),
            "--temp",
            str(textile_env["stamped_dir"]),
            "--stamps",
            str(textile_env["stamps_dir"]),
            "--template",
            str(textile_env["template_path"]),
        ]

        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        assert proc.returncode == 0, f"CLI 執行失敗: {proc.stderr}\n{proc.stdout}"

        # 1. 驗證 temp 目錄蓋章產物
        stamped_files = sorted([f.name for f in textile_env["stamped_dir"].glob("*.pdf")])
        expected_stamped = sorted([
            "採購單~1 1.pdf",
            "請購單~2 1.pdf",
            "進貨單~2 1.pdf",
            "進貨驗收單~2 1.pdf",
        ])
        assert stamped_files == expected_stamped, "temp/stamped 應包含 4 個蓋章 PDF"

        # 2. 驗證 output 目錄產物
        merged_pdf = textile_env["output_dir"] / "1011506080001-GL012-金利多企.pdf"
        excel_path = textile_env["output_dir"] / "1011506080001-單據明細.xlsx"
        log_files = list(textile_env["output_dir"].glob("*.log"))

        assert merged_pdf.exists(), f"合併 PDF 應存在: {merged_pdf.name}"
        assert excel_path.exists(), f"明細 Excel 應存在: {excel_path.name}"
        assert len(log_files) == 1, "應產出 1 份執行日誌"

        # 3. 驗證合併 PDF 內容與單據順序
        doc = fitz.open(merged_pdf)
        try:
            assert len(doc) == 4, "合併單據應為 4 頁"
            # 順序：進貨單 > 進貨驗收單 > 採購單 > 請購單
            assert "進貨單" in doc[0].get_text()
            assert "進貨驗收單" in doc[1].get_text()
            assert "採購單" in doc[2].get_text()
            assert "請購單" in doc[3].get_text()

            # 進貨驗收單頁（index 1）應有 3 個印章
            assert len(doc[1].get_images()) == 3, "進貨驗收單頁應有 3 個印章"
        finally:
            doc.close()

        # 4. 驗證 Excel 明細數據
        wb = load_workbook(excel_path)
        ws = wb.active
        assert ws["B3"].value == 1, "B3 支數應為 1"
        assert ws["C3"].value == 1, "C3 張數應為 1"
        assert ws["G2"].value == "1011506080001", "G2 採購單號應為 1011506080001"
        wb.close()

        # 5. 驗證日誌包含全數成功摘要
        log_text = log_files[0].read_text(encoding="utf-8")
        assert "總計: 成功 6" in log_text and "所有處理已成功完成" in log_text
