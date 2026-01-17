"""請購單蓋章模組"""

from .base import StampConfig

# 請購單印章配置
# 「製表」欄位位置：x=425~447, y=809.3
# 印章放在「製表」欄位右側
STAMP_CONFIG_CREATOR = StampConfig(
    x=452.0,
    y=806.0,
    target_width=32.0,
    target_height=17.0,
)

# 預設印章檔名
DEFAULT_CREATOR_STAMP = "雅萍.png"
