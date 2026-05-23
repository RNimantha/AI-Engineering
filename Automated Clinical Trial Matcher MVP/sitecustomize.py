"""
Notebook import bootstrap for the clinical trial matcher project.

If Python starts inside `Automated Clinical Trial Matcher MVP`, make the
sdk-comparison shared helpers importable as `shared.*`.
"""

from __future__ import annotations

import sys
from pathlib import Path


SDK_COMPARISON_DIR = Path(__file__).resolve().parent / "sdk-comparison"

if SDK_COMPARISON_DIR.is_dir():
    sdk_path = str(SDK_COMPARISON_DIR)
    if sdk_path not in sys.path:
        sys.path.insert(0, sdk_path)
