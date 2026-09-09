"""紡織類樣本端到端全流程驗證（Phase 0 ~ Phase 2）與回歸測試套件

驗收 Issue #4：
1. 端到端執行 Phase 0，驗證紡織類四類單據產出均符合預期對照印章配置。
2. 比對 Phase 0 產出 PDF 圖片數量與座標中心點，確認在預期公差範圍內。
3. 驗證 Phase 1 產出合併 PDF 命名為 1011506080001-GL012-金利多企.pdf（ERP 原生文字層簡稱截斷），且順序為 進貨單 > 進貨驗收單 > 採購單 > 請購單。
4. 驗證 Phase 2 正確產出 Excel 單據明細表，且張數（1 張，依單據號碼計）與支數（1 支）正確填入 B3 與 C3。
5. 確保全流程各階段與既有測試整合相容。
"""

import shutil
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
            "進貨驗收單~2 1.pdf": "進貨驗收單_2.pdf",
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
                # 紡織類進貨驗收單應有 2 個印章：進料檢驗章與製單章，嚴格排除倉管章
                assert len(act_images) == 2, "紡織類進貨驗收單應只有 2 個印章"

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
                act_center_x = (act_rect.x0 + act_rect.x1) / 2
                act_center_y = (act_rect.y0 + act_rect.y1) / 2
                exp_center_x = (exp_rect.x0 + exp_rect.x1) / 2
                exp_center_y = (exp_rect.y0 + exp_rect.y1) / 2

                diff_x = abs(act_center_x - exp_center_x)
                diff_y = abs(act_center_y - exp_center_y)

                # 進料檢驗章（寬度 > 100 pt）因等比例縮放高為 153 pt（原目標框高 166.7 pt），中心 y 偏移約 6.8 pt，加計 ±3pt 自然化抖動上限約 9.8 pt
                is_inspection = act_rect.width > 100
                max_diff_x = 5.5
                max_diff_y = 10.0 if is_inspection else 4.5

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
                    assert abs(act_rect.width - 32.1) <= 3.5, (
                        f"{actual_name} 職章寬度應約 32.1 pt"
                    )
                    assert abs(act_rect.height - 17.3) <= 3.5, (
                        f"{actual_name} 職章高度應約 17.3 pt"
                    )

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
