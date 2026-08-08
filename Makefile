.PHONY: install test reproduce figs tables clean notebook archive
PY ?= python3
install:
	$(PY) -m pip install -e ".[dev]"
test:
	$(PY) -m pytest tests/ -v
reproduce:
	$(PY) scripts/run_study.py --synthetic
	$(PY) scripts/make_assets.py
figs tables:
	$(PY) scripts/make_assets.py
notebook:
	$(PY) -m jupyter lab notebooks/SignalShap_Reproduction.ipynb
# Immutable submission archive for Zenodo. Excludes raw corpora (not ours to
# redistribute), git internals, and caches. Upload the zip to a Zenodo draft
# that already has a reserved DOI.
archive:
	@rm -f signalshap-archive.zip
	@git archive --format=zip --prefix=signalshap-code/ -o signalshap-archive.zip HEAD
	@rm -rf .archive_tmp && mkdir -p .archive_tmp/signalshap-code
	@cp -r artefacts .archive_tmp/signalshap-code/
	@find .archive_tmp -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	@cd .archive_tmp && zip -qr ../signalshap-archive.zip signalshap-code
	@rm -rf .archive_tmp
	@echo "signalshap-archive.zip built from commit $$(git rev-parse --short HEAD)"
	@echo "reserve the DOI on Zenodo FIRST, paste it into sn-article.tex, then re-run this target"

clean:
	rm -rf artefacts/figures artefacts/tables artefacts/*.json
	find . -name __pycache__ -type d -exec rm -rf {} +
