"""模組入口點，允許 python -m doc_processor 執行"""

import sys

from .cli import main

sys.exit(main())
