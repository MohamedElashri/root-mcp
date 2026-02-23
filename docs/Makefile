# Minimal Sphinx Makefile
# Usage:
#   make html          — build HTML docs  (output: _build/html/)
#   make livehtml      — live-reload server at http://localhost:8000
#   make linkcheck     — check all external / internal links
#   make clean         — remove _build/

# Default: lenient build — see all warnings but don't fail on them.
# For strict CI-style build: make strict  (or SPHINXOPTS="-W --keep-going" make html)
SPHINXOPTS    ?= --keep-going
SPHINXBUILD   ?= uv run sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

.PHONY: help html livehtml linkcheck clean Makefile

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

html:
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@echo
	@echo "Build finished → $(BUILDDIR)/html/index.html"

livehtml:
	uv run sphinx-autobuild \
	  --watch ../src \
	  --open-browser \
	  "$(SOURCEDIR)" "$(BUILDDIR)/html" $(O)

linkcheck:
	@$(SPHINXBUILD) -b linkcheck "$(SOURCEDIR)" "$(BUILDDIR)/linkcheck" $(O)
	@echo
	@echo "Link check output → $(BUILDDIR)/linkcheck/output.txt"

strict:
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" -W --keep-going $(O)
	@echo
	@echo "Strict build finished → $(BUILDDIR)/html/index.html"

clean:
	rm -rf "$(BUILDDIR)"
	@echo "Build directory removed."

# Catch-all target: route all unknown targets to Sphinx
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
