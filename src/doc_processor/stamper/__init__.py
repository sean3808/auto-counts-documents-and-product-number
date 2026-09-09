"""PDF 蓋章模組"""

from .base import StampConfig, find_vendor_stamp, scale_image_to_fit, stamp_pdf
from .purchase_order import stamp_purchase_order
from .receiving import (
    calculate_inspection_stamp_y,
    get_inspection_stamp_config,
    stamp_receiving,
)

__all__ = [
    "StampConfig",
    "calculate_inspection_stamp_y",
    "find_vendor_stamp",
    "get_inspection_stamp_config",
    "scale_image_to_fit",
    "stamp_pdf",
    "stamp_purchase_order",
    "stamp_receiving",
]
