# tests/conftest.py
"""Pytest configuration.
Shared pytest configuration for the py_mcmd test suite.

Tests use the canonical py_mcmd package namespace and are intended
to run from the repository root.
"""

# This repository is intentionally kept lightweight and does not require an
# editable install for unit tests. To make `pytest` runnable from the repo root
# in any environment, we add the project package root to `sys.path`.

# The project package root is the directory that contains `config/`, `cli/`,
# `orchestrator/`, `engines/`, and `utils/`.
# """

# from __future__ import annotations

# import sys
# from pathlib import Path


# def _ensure_project_on_syspath() -> None:
#     tests_dir = Path(__file__).resolve().parent
#     project_root = tests_dir.parent  # <repo>/py_mcmd
#     repo_root = project_root.parent  # <repo>

#     for p in (str(repo_root), str(project_root)):
#         if p not in sys.path:
#             sys.path.insert(0, p)


# _ensure_project_on_syspath()
