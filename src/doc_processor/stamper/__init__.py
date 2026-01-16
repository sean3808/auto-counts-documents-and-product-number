"""PDF 蓋章模組"""

from .base import StampConfig, find_vendor_stamp, scale_image_to_fit, stamp_pdf

__all__ = ["StampConfig", "find_vendor_stamp", "scale_image_to_fit", "stamp_pdf"]
