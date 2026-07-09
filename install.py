#!/usr/bin/env python3
"""Thin Wise Owl user-local installer shortcut."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INSTALLER = ROOT / ".agents" / "skills" / "wise-owl" / "scripts" / "wise_owl_install.py"


def main() -> int:
    args = sys.argv[1:]
    os.environ["WISE_OWL_INSTALL_PROG"] = Path(sys.argv[0]).name
    sys.argv = [str(INSTALLER), *args]
    runpy.run_path(str(INSTALLER), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
