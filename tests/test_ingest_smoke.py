"""Smoke test for ingest module."""

from __future__ import annotations
from pathlib import Path
import pytest

from src.common.paths import ProjectPaths


def test_project_paths():
    """Test that ProjectPaths builds correct paths."""
    root = Path(".").resolve()
    paths = ProjectPaths(root)
    
    assert paths.configs == root / "configs"
    assert paths.data == root / "data"
    assert paths.raw == root / "data" / "raw"
    assert paths.canonical == root / "data" / "canonical"


def test_ingest_imports():
    """Test that ingest modules can be imported."""
    from src.ingest.run_ingest import main
    from src.ingest.cftc_downloader import download_file
    from src.ingest.manifest import load_manifest, append_manifest
    
    assert main is not None
    assert download_file is not None
    assert load_manifest is not None
