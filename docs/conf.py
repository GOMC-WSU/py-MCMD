"""Sphinx configuration for the py-MCMD user manual."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from py_mcmd_refactored.version import get_version

project = "py-MCMD"
author = "Crawford, B., Mehryar H., Potoff J., Schwiebert L., and Uddin N."
copyright = "2021-2026"
version = get_version()
release = version

# The manual contains no API-reference or notebook pages, so its build has few
# dependencies and does not import simulation-engine packages.
extensions = ["sphinx.ext.mathjax"]
templates_path = ["_templates"]
exclude_patterns = ["_build", "**.ipynb_checkpoints"]
source_suffix = ".rst"
master_doc = "index"
pygments_style = "sphinx"

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
htmlhelp_basename = "py-MCMD_doc"
