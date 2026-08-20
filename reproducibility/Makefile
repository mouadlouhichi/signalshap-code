# SignalShap reproducibility release.
.PHONY: help install conda test synthetic assets manifest verify clean
export PYTHONPATH := src

help:
	@echo "make install    install dependencies (pip)"
	@echo "make conda      create the conda environment"
	@echo "make test       run the test suite (no data needed)"
	@echo "make synthetic  end-to-end run on planted synthetic corpora"
	@echo "make assets     regenerate figures and tables from artefacts/"
	@echo "make manifest   recompute artefact SHA-256 hashes"
	@echo "make verify     test + manifest"
	@echo ""
	@echo "Real corpora: see README, 'Reproducing the paper'."

install:
	pip install -r requirements.txt

conda:
	conda env create -f environment.yml

test:
	python -m pytest tests/ -q

synthetic:
	python experiments/run_study.py --synthetic --datasets ml_1m --seeds 42 43

assets:
	python scripts/make_assets.py

manifest:
	python scripts/make_manifest.py

verify: test manifest

clean:
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
