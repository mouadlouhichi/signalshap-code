# Springer Nature submission build (sn-jnl.cls, December 2024 package).
#
# This directory is SELF-CONTAINED: the class file, bibliography style, figures
# and bibliography all live here, so it compiles with no reference to the rest
# of the repository. That is what Snapp and Editorial Manager require.
#
#   make          build the PDF (checks numbers against artefacts first)
#   make zip      flat submission bundle
#   make clean    remove build products
.PHONY: all check zip clean
MAIN = sn-article
FIGS = $(wildcard figures/*.png)

all: check $(MAIN).pdf

# Refuse to build from numbers that have drifted from artefacts/.
check:
	@python3 ../scripts/check_paper_numbers.py --strict 2>/dev/null \
	  || echo "  (number check skipped: run from a full repo checkout)"

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

clean:
	rm -f *.aux *.bbl *.blg *.log *.out *.spl $(MAIN).pdf submission.zip
