"""進貨單蓋章模組"""

from .base import StampConfig

# 進貨單印章配置
# 「製表」欄位位置：x=162~180, y=800.2
# 印章放在「製表」欄位右側
STAMP_CONFIG_CREATOR = StampConfig(
    x=194.0,
    y=799.7,
    target_width=32.1,
    target_height=17.3,
)

# 預設印章檔名
DEFAULT_CREATOR_STAMP = "雅萍.png"
