"""PDF 蓋章模組"""

from .base import StampConfig, find_vendor_stamp, scale_image_to_fit, stamp_pdf
from .purchase_order import stamp_purchase_order
from .receiving import stamp_receiving

__all__ = [
    "StampConfig",
    "find_vendor_stamp",
    "scale_image_to_fit",
    "stamp_pdf",
    "stamp_purchase_order",
    "stamp_receiving",
]
