#!/usr/bin/env bash
# build_docs.sh — Full documentation build pipeline for ROOT-MCP
#
# Usage:
#   ./scripts/build_docs.sh              # lenient HTML build (default)
#   STRICT=1 ./scripts/build_docs.sh     # strict build: warnings = errors (for CI)
#   LINKCHECK=1 ./scripts/build_docs.sh  # also run link checker after HTML build
#   STRICT=1 LINKCHECK=1 ./scripts/build_docs.sh  # full CI pipeline
#
# Environment variables:
#   STRICT     — set to "1" to enable -W (warnings as errors)
#   LINKCHECK  — set to "1" to run sphinx linkcheck after the HTML build
#
# Dependencies: uv must be available. Run from any directory inside the repo.

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve paths relative to this script regardless of cwd
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCS_DIR="$REPO_DIR/docs"
SRC_DIR="$REPO_DIR/src"
APIDOC_OUT="$DOCS_DIR/apidoc/root_mcp"
BUILD_DIR="$DOCS_DIR/_build"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo "[build_docs] $*"; }
error() { echo "[build_docs] ERROR: $*" >&2; exit 1; }

command -v uv >/dev/null 2>&1 || error "'uv' not found. Install from https://docs.astral.sh/uv/"

# ---------------------------------------------------------------------------
# Step 1 — Install documentation dependencies
# ---------------------------------------------------------------------------
info "Installing documentation dependencies…"
uv pip install -q -r "$DOCS_DIR/requirements.txt"

# ---------------------------------------------------------------------------
# Step 2 — Regenerate sphinx-apidoc stubs (always fresh)
# ---------------------------------------------------------------------------
info "Regenerating sphinx-apidoc stubs → $APIDOC_OUT"
uv run sphinx-apidoc \
    --output-dir "$APIDOC_OUT" \
    --module-first \
    --separate \
    --force \
    "$SRC_DIR/root_mcp"

# ---------------------------------------------------------------------------
# Step 3 — Build HTML
# ---------------------------------------------------------------------------
SPHINX_OPTS="--keep-going"
if [[ "${STRICT:-0}" == "1" ]]; then
    SPHINX_OPTS="-W $SPHINX_OPTS"
    info "Strict mode enabled (warnings = errors)"
fi

info "Building HTML docs…"
# shellcheck disable=SC2086  # intentional word-splitting for SPHINX_OPTS
uv run sphinx-build -b html $SPHINX_OPTS "$DOCS_DIR" "$BUILD_DIR/html"

# ---------------------------------------------------------------------------
# Step 4 — Optional linkcheck
# ---------------------------------------------------------------------------
if [[ "${LINKCHECK:-0}" == "1" ]]; then
    info "Running link checker…"
    uv run sphinx-build -b linkcheck "$DOCS_DIR" "$BUILD_DIR/linkcheck"
    info "Link check output → $BUILD_DIR/linkcheck/output.txt"
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
info "Done — open $BUILD_DIR/html/index.html"
