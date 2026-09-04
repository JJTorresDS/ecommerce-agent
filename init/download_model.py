"""Backward-compatible entry. Prefer: uv run python db/download_model.py"""

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parent.parent / "db" / "download_model.py"),
        run_name="__main__",
    )
