"""Shared pytest fixtures for ASO skill tests."""
import os
import sys
import pytest

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")

sys.path.insert(0, SCRIPTS_DIR)


@pytest.fixture
def skill_dir():
    return SKILL_DIR


@pytest.fixture
def assets_dir():
    return os.path.join(SKILL_DIR, "assets")


@pytest.fixture
def sample_ui_path():
    return os.path.join(SKILL_DIR, "tests", "fixtures", "sample_ui.png")


@pytest.fixture
def tmp_output(tmp_path):
    """A clean tmp output path for each test."""
    return str(tmp_path / "output.png")
