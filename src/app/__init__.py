"""Streamlit app package."""

from pathlib import Path
import sys

# --- PYTHONPATH bootstrap ---
# Ensure repo root is on sys.path so `import src.*` works in Streamlit multipage.
# This runs automatically when any module from src.app is imported.
_REPO_ROOT = Path(__file__).resolve().parents[2]  # .../COT_v1 (repo root)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
# ---------------------------
