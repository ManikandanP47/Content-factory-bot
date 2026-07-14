"""Content Factory — local short-form production pipeline."""

from pathlib import Path

__version__ = "0.1.0"

PACKAGE_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PACKAGE_ROOT.parent
PROJECT_ROOT = SRC_ROOT.parent
