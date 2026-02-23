# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from __future__ import annotations

import os
import sys
from importlib.metadata import PackageNotFoundError, version as _dist_version

# Make root_mcp importable from source without an installed wheel
sys.path.insert(0, os.path.abspath("../src"))

# ---------------------------------------------------------------------------
# Project metadata
# ---------------------------------------------------------------------------

try:
    _pkg_version = _dist_version("root-mcp")
except PackageNotFoundError:
    _pkg_version = "0.0.0"

project = "ROOT-MCP"
author = "Mohamed Elashri"
copyright = "2026, Mohamed Elashri"  # noqa: A001
version = ".".join(_pkg_version.split(".")[:2])  # short X.Y
release = _pkg_version  # full X.Y.Z

# ---------------------------------------------------------------------------
# General configuration
# ---------------------------------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "myst_parser",
    "sphinx_copybutton",
    "sphinxawesome_theme",
]

# Accept both RST and Markdown source files
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "myst",
}

# Root document
root_doc = "index"

# Patterns to exclude from the build
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    # Raw guides are included via wrapper RST files; exclude them from
    # appearing as top-level documents so they don't show up twice.
    "guides/*.md",
    "api/*.md",
    "ARCHITECTURE.md",
    "CONTRIBUTING.md",
    "README.md",
]

templates_path = ["_templates"]
html_static_path = ["_static"]

# ---------------------------------------------------------------------------
# HTML / Theme
# ---------------------------------------------------------------------------

html_theme = "sphinxawesome_theme"

html_theme_options = {
    "show_breadcrumbs": True,
    "show_prev_next": True,
    "main_nav_links": {
        "Docs": "index",
        "GitHub": "https://github.com/MohamedElashri/root-mcp",
    },
    "extra_footer": (
        "Built with "
        '<a href="https://github.com/kai687/sphinxawesome-theme" '
        'target="_blank" rel="noopener">Sphinx Awesome Theme</a>.'
    ),
}

html_css_files = ["custom.css"]

html_logo = "_static/root-mcp_logo.png"
html_favicon = "_static/root-mcp_logo.png"

html_title = f"ROOT-MCP {release}"

# ---------------------------------------------------------------------------
# MyST-Parser
# ---------------------------------------------------------------------------

myst_enable_extensions = [
    "colon_fence",  # ::: admonition shorthand
    "deflist",  # definition lists
    "substitution",  # |variable| substitutions
    "tasklist",  # - [x] checkboxes
]

myst_heading_anchors = 3  # auto-generate anchors for h1–h3

# ---------------------------------------------------------------------------
# Autodoc
# ---------------------------------------------------------------------------

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "special-members": "__init__",
}

autodoc_typehints = "description"
autodoc_typehints_format = "short"

# Mock optional heavy dependencies so the build works in a minimal environment
# (e.g., CI without ROOT, uproot, scipy installed).
autodoc_mock_imports = [
    "ROOT",
    "uproot",
    "awkward",
    "scipy",
    "matplotlib",
    "pyarrow",
    "fsspec",
    "xxhash",
    "aiofiles",
    "XRootD",
    "mcp",
    "pydantic",
    "pydantic_settings",
]

# ---------------------------------------------------------------------------
# Napoleon (Google-style docstrings)
# ---------------------------------------------------------------------------

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True

# ---------------------------------------------------------------------------
# Intersphinx — cross-link to external docs
# ---------------------------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
}

# ---------------------------------------------------------------------------
# Copy button
# ---------------------------------------------------------------------------

copybutton_prompt_text = r"^\$ |^>>> "
copybutton_prompt_is_regexp = True

# ---------------------------------------------------------------------------
# Suppress known false positives
# ---------------------------------------------------------------------------

# These warnings arise because the included .md files contain GitHub-relative
# links (e.g. [modes.md](modes.md)) that made sense on GitHub but cannot be
# resolved inside the Sphinx build.  Suppressing them keeps the output clean
# without hiding genuine documentation errors.
#
# misc.highlighting_failure: JSON code blocks in the tool reference use
#   pseudo-notation (...) which is not valid JSON; the Pygments lexer falls
#   back to plain text automatically — no content is lost.
suppress_warnings = [
    "myst.xref_missing",  # relative .md cross-links in included files
    "misc.highlighting_failure",  # JSON examples with pseudo-notation (...)
    "ref.any",  # unknown docutils target names from .md links
    "ref.python",  # ambiguous cross-refs where a name is re-exported
    # at multiple levels (Config, FileManager, etc.)
    "autodoc",  # @classmethod validator signatures (Pydantic internals)
]
