"""列印校正診斷腳本（含 TW111 印章）

此腳本在 PDF 中繪製已知尺寸的參考線段和框線，
並放入 TW111 印章實際圖片，用於驗證列印環境的縮放比例。

使用方式：
    uv run python scripts/print_calibration_test.py

輸出：
    output/print_calibration_test.pdf

驗證步驟：
    1. 以「實際大小 100%」列印 PDF
    2. 用尺測量水平線和垂直線的實際長度
    3. 測量 TW111 印章的實際尺寸
    4. 根據測量結果調整 purchase_order.py 中的配置

預期尺寸：
    - 參考框線：127.56 pt = 4.5 cm × 85.04 pt = 3.0 cm
    - TW111 印章：依配置 239 × 159 pt（目標列印 4.5 × 3.0 cm）
"""

import sys
from pathlib import Path

import fitz
from PIL import Image

# 加入 src 路徑以便引用專案模組
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doc_processor.stamper.base import scale_image_to_fit
from doc_processor.stamper.purchase_order import STAMP_CONFIG_VENDOR_TW111


def create_calibration_pdf(output_path: Path, stamp_path: Path | None = None) -> None:
    """建立校正用 PDF"""
    # A4 尺寸 (pt)
    page_width = 595.28
    page_height = 841.89

    # 參考框線目標尺寸 (pt)
    # 4.5 cm = 4.5 / 2.54 * 72 = 127.56 pt
    # 3.0 cm = 3.0 / 2.54 * 72 = 85.04 pt
    ref_width_pt = 127.56
    ref_height_pt = 85.04

    doc = fitz.open()
    page = doc.new_page(width=page_width, height=page_height)

    # 頁面位置設定
    center_x = page_width / 2
    margin_left = 80
    font_size = 10
    text_color = (0, 0, 0)

    # === 標題 ===
    page.insert_text(
        fitz.Point(center_x - 120, 60),
        "列印校正測試（含 TW111 印章）",
        fontsize=18,
        color=text_color,
    )

    # === 區塊 1：參考框線 (4.5 cm × 3.0 cm) ===
    section1_y = 120
    page.insert_text(
        fitz.Point(margin_left, section1_y),
        "【參考框線】4.5 cm × 3.0 cm",
        fontsize=12,
        color=(0, 0, 0.7),
    )

    # 繪製參考框線
    ref_x0 = margin_left
    ref_y0 = section1_y + 20
    ref_x1 = ref_x0 + ref_width_pt
    ref_y1 = ref_y0 + ref_height_pt

    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(ref_x0, ref_y0, ref_x1, ref_y1))
    shape.finish(color=(0, 0, 0), width=1.5)
    shape.commit()

    # 水平標註線和文字（框上方）
    shape = page.new_shape()
    shape.draw_line(fitz.Point(ref_x0, ref_y0 - 8), fitz.Point(ref_x1, ref_y0 - 8))
    shape.finish(color=(1, 0, 0), width=1)
    shape.commit()
    page.insert_text(
        fitz.Point(ref_x0, ref_y0 - 12),
        f"← {ref_width_pt:.2f} pt = 4.5 cm →",
        fontsize=8,
        color=(1, 0, 0),
    )

    # 垂直標註線和文字（框左側）
    shape = page.new_shape()
    shape.draw_line(fitz.Point(ref_x0 - 8, ref_y0), fitz.Point(ref_x0 - 8, ref_y1))
    shape.finish(color=(0, 0, 1), width=1)
    shape.commit()
    page.insert_text(
        fitz.Point(ref_x0 - 55, ref_y0 + ref_height_pt / 2 + 30),
        f"{ref_height_pt:.2f} pt = 3.0 cm",
        fontsize=8,
        color=(0, 0, 1),
        rotate=90,
    )

    # === 區塊 2：TW111 印章實際圖片 ===
    section2_y = ref_y1 + 60
    page.insert_text(
        fitz.Point(margin_left, section2_y),
        "【TW111 印章實際圖片】",
        fontsize=12,
        color=(0, 0.5, 0),
    )

    # 顯示配置資訊
    config_width = STAMP_CONFIG_VENDOR_TW111.target_width
    config_height = STAMP_CONFIG_VENDOR_TW111.target_height
    page.insert_text(
        fitz.Point(margin_left, section2_y + 15),
        f"配置目標框：{config_width:.0f} × {config_height:.0f} pt",
        fontsize=9,
        color=(0.3, 0.3, 0.3),
    )

    stamp_x0 = margin_left
    stamp_y0 = section2_y + 35

    if stamp_path and stamp_path.exists():
        # 讀取印章圖片尺寸
        with Image.open(stamp_path) as img:
            orig_w, orig_h = img.size

        # 計算縮放後尺寸
        new_w, new_h = scale_image_to_fit(
            orig_w, orig_h, config_width, config_height
        )

        # 插入印章圖片
        stamp_rect = fitz.Rect(stamp_x0, stamp_y0, stamp_x0 + new_w, stamp_y0 + new_h)
        page.insert_image(stamp_rect, filename=str(stamp_path))

        # 繪製實際渲染框線（虛線）
        shape = page.new_shape()
        shape.draw_rect(stamp_rect)
        shape.finish(color=(0, 0.5, 0), width=0.5, dashes="[3 3]")
        shape.commit()

        # 標註實際渲染尺寸
        info_y = stamp_y0 + new_h + 15
        page.insert_text(
            fitz.Point(margin_left, info_y),
            f"原始圖片：{orig_w} × {orig_h} px",
            fontsize=9,
            color=(0.3, 0.3, 0.3),
        )
        page.insert_text(
            fitz.Point(margin_left, info_y + 12),
            f"實際渲染：{new_w:.2f} × {new_h:.2f} pt",
            fontsize=9,
            color=(0, 0.5, 0),
        )
        # 換算為 cm
        render_cm_w = new_w * 2.54 / 72
        render_cm_h = new_h * 2.54 / 72
        page.insert_text(
            fitz.Point(margin_left, info_y + 24),
            f"預期列印：{render_cm_w:.2f} × {render_cm_h:.2f} cm",
            fontsize=9,
            color=(0, 0.5, 0),
        )

        next_section_y = info_y + 50
    else:
        page.insert_text(
            fitz.Point(margin_left, stamp_y0),
            f"⚠ 找不到印章檔案：{stamp_path}",
            fontsize=10,
            color=(0.8, 0, 0),
        )
        next_section_y = stamp_y0 + 40

    # === 測量說明 ===
    page.insert_text(
        fitz.Point(margin_left, next_section_y),
        "【測量說明】",
        fontsize=12,
        color=text_color,
    )

    instructions = [
        "1. 以「實際大小 100%」列印此 PDF",
        "2. 用尺測量參考框線，驗證列印無縮放：",
        "   - 水平應 = 4.5 cm",
        "   - 垂直應 = 3.0 cm",
        "3. 測量 TW111 印章的實際寬度和高度",
        "4. 若印章尺寸不符預期，根據以下公式調整：",
        "",
        "   新目標 pt = 當前目標 pt × (期望尺寸 / 實測尺寸)",
        "",
        "   範例：期望 4.5 cm，實測 5.0 cm",
        f"   新目標寬度 = {config_width:.0f} × (4.5 / 5.0) = {config_width * 4.5 / 5.0:.1f} pt",
    ]

    y_pos = next_section_y + 18
    for line in instructions:
        page.insert_text(
            fitz.Point(margin_left, y_pos),
            line,
            fontsize=9,
            color=text_color,
        )
        y_pos += 13

    # === 當前配置摘要 ===
    summary_y = y_pos + 20
    page.insert_text(
        fitz.Point(margin_left, summary_y),
        "【當前配置摘要】",
        fontsize=12,
        color=text_color,
    )

    page.insert_text(
        fitz.Point(margin_left, summary_y + 18),
        f"STAMP_CONFIG_VENDOR_TW111:",
        fontsize=9,
        color=(0.3, 0.3, 0.3),
    )
    page.insert_text(
        fitz.Point(margin_left + 20, summary_y + 30),
        f"target_width = {config_width:.0f} pt",
        fontsize=9,
        color=(0.3, 0.3, 0.3),
    )
    page.insert_text(
        fitz.Point(margin_left + 20, summary_y + 42),
        f"target_height = {config_height:.0f} pt",
        fontsize=9,
        color=(0.3, 0.3, 0.3),
    )

    # 儲存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    doc.close()
    print(f"已建立校正 PDF：{output_path}")


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "output"
    output_path = output_dir / "print_calibration_test.pdf"

    # TW111 印章路徑
    stamp_path = project_root / "印章" / "removebg" / "TW111.png"

    create_calibration_pdf(output_path, stamp_path)
