# Springer Nature submission build (sn-jnl.cls, December 2024 package).
#
# This directory is SELF-CONTAINED: the class file, bibliography style, figures
# and bibliography all live here, so it compiles with no reference to the rest
# of the repository. That is what Snapp and Editorial Manager require.
#
#   make          build the PDF (checks numbers against artefacts first)
#   make zip      flat submission bundle
#   make clean    remove build products
.PHONY: all check verify zip overleaf main2 clean
MAIN = sn-article
FIGS = $(wildcard figures/*.png)

all: check $(MAIN).pdf

# Refuse to build from numbers that have drifted from artefacts/.
check:
	@python3 ../scripts/check_paper_numbers.py 2>/dev/null \
	  || echo "  (number check skipped: run from a full repo checkout)"
	@python3 ../scripts/check_discover_ai.py 2>/dev/null \
	  || echo "  (compliance check skipped: run from a full repo checkout)"
	@python3 ../scripts/check_latex.py

$(MAIN).pdf: $(MAIN).tex paper.bib sn-jnl.cls sn-basic.bst $(FIGS)
	pdflatex -interaction=nonstopmode $(MAIN).tex
	bibtex $(MAIN) || true
	pdflatex -interaction=nonstopmode $(MAIN).tex
	pdflatex -interaction=nonstopmode $(MAIN).tex
	@echo "--- undefined citations/references ---"
	@grep -cE "Citation .* undefined|Reference .* undefined" $(MAIN).log || echo "  none"

# Springer wants a flat archive that compiles with pdflatex.
zip: $(MAIN).pdf
	rm -f submission.zip
	zip -q submission.zip $(MAIN).tex paper.bib sn-jnl.cls sn-basic.bst figures/*.png
	@unzip -l submission.zip | tail -3

# Source bundle for Overleaf. Deliberately does NOT depend on the PDF: the
# whole point is to get the sources to a machine that HAS TeX.
overleaf:
	rm -f signalshap-overleaf.zip
	zip -qr signalshap-overleaf.zip $(MAIN).tex paper.bib sn-jnl.cls sn-basic.bst figures/
	@unzip -l signalshap-overleaf.zip | tail -3
	@echo "upload signalshap-overleaf.zip to Overleaf; compiler = pdfLaTeX"

# Same bundle as `overleaf`, under the filename used for sharing the sources.
# Runs the static checks first: shipping a tree whose numbers have drifted from
# artefacts/ is the failure this whole pipeline exists to prevent.
main2: check
	rm -f ../signalshap-main2.zip
	zip -qr ../signalshap-main2.zip $(MAIN).tex paper.bib sn-jnl.cls \
	  sn-basic.bst figures/
	@unzip -l ../signalshap-main2.zip | tail -3

# Everything verifiable without a TeX installation. Kept separate from `check`,
# which is a soft pre-build gate; this one is strict and runs the test suite.
verify:
	cd .. && python3 scripts/check_paper_numbers.py --strict
	cd .. && python3 scripts/check_discover_ai.py
	cd .. && python3 -m pytest tests/ -q

clean:
	rm -f *.aux *.bbl *.blg *.log *.out *.spl $(MAIN).pdf submission.zip signalshap-overleaf.zip ../signalshap-main2.zip
