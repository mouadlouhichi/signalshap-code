.PHONY: install test reproduce figs tables clean notebook
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
clean:
	rm -rf artefacts/figures artefacts/tables artefacts/*.json
	find . -name __pycache__ -type d -exec rm -rf {} +
