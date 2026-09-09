"""產線印章圖檔完整性與資產規範測試"""

from pathlib import Path
from PIL import Image

STAMPS_REMOVEBG_DIR = Path("印章/removebg")


class TestProductionStampAssets:
    """測試產線已去背印章資產完整性與乾淨度"""

    def test_stamps_removebg_directory_exists(self):
        """確認印章/removebg/ 目錄存在"""
        assert STAMPS_REMOVEBG_DIR.is_dir(), "印章/removebg/ 目錄必須存在"

    def test_core_role_stamps_exist(self):
        """確認四個核心角色印章均存在：雅萍、簡銘佑、莊宛恬、紡織進料檢"""
        required_stamps = [
            "雅萍.png",
            "簡銘佑.png",
            "莊宛恬.png",
            "紡織進料檢.png",
        ]
        for stamp_name in required_stamps:
            stamp_path = STAMPS_REMOVEBG_DIR / stamp_name
            assert stamp_path.is_file(), f"核心印章缺失: {stamp_name}"

    def test_zhuang_wantian_stamp_image_integrity(self):
        """確認莊宛恬印章為有效 RGBA PNG 且具備透明通道"""
        zhuang_path = STAMPS_REMOVEBG_DIR / "莊宛恬.png"
        assert zhuang_path.is_file(), "莊宛恬.png 不存在"

        with Image.open(zhuang_path) as img:
            assert img.format == "PNG", "圖片格式必須為 PNG"
            assert img.mode == "RGBA", "色彩模式必須為 RGBA"
            alpha = img.split()[-1]
            min_alpha, max_alpha = alpha.getextrema()
            assert min_alpha == 0, "印章背景必須有完全透明區域 (alpha=0)"
            assert max_alpha == 255, "印章線條必須有完全不透明區域 (alpha=255)"

    def test_no_backup_files_in_removebg(self):
        """確認印章/removebg/ 下無任何 backup 備份檔案"""
        backup_files = list(STAMPS_REMOVEBG_DIR.glob("*backup*"))
        assert len(backup_files) == 0, f"印章/removebg/ 不得包含備份檔案: {[f.name for f in backup_files]}"

    def test_no_trimed_directory_in_removebg(self):
        """確認印章/removebg/ 下無歷史 trimed/ 備份目錄"""
        trimed_dir = STAMPS_REMOVEBG_DIR / "trimed"
        assert not trimed_dir.exists(), "印章/removebg/trimed/ 目錄應已清理"

    def test_all_pngs_are_valid_rgba(self):
        """確認印章/removebg/ 下的所有 PNG 皆為有效 RGBA 圖檔"""
        png_files = list(STAMPS_REMOVEBG_DIR.glob("*.png"))
        assert len(png_files) > 0, "印章/removebg/ 下應有 PNG 圖檔"

        for png_file in png_files:
            with Image.open(png_file) as img:
                assert img.format == "PNG", f"{png_file.name} 必須為 PNG 格式"
                assert img.mode == "RGBA", f"{png_file.name} 必須為 RGBA 模式"
