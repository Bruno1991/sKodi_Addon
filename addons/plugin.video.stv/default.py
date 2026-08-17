from __future__ import annotations

import os
import sys

LIB_DIR = os.path.join(os.path.dirname(__file__), "resources", "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from stv.bootstrap import run  # noqa: E402


if __name__ == "__main__":
    run(sys.argv)
