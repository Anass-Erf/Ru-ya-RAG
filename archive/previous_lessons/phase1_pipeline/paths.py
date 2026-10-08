"""One data root for the existing review-only pipeline."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.environ.get("RUYA_DATA_DIR", PROJECT_ROOT / "data")).resolve()
