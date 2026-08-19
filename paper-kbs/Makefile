# Knowledge-Based Systems (Elsevier) build.
#
# kbs-article.tex is GENERATED from ../paper/sn-article.tex by
# ../scripts/make_elsevier.py. Do not edit it by hand: the Springer file is
# the source of truth for prose and numbers, and check_paper_numbers.py
# validates that file against artefacts/. A hand-forked copy would drift.
#
#   make regen    rebuild kbs-article.tex from the Springer source
#   make          checks, then the PDF
#   make zip      flat submission bundle for Editorial Manager
#   make clean    remove build products
.PHONY: all regen check zip clean
MAIN = kbs-article
FIGS = $(wildcard figures/*.png)

all: check $(MAIN).pdf

regen:
	cd .. && python3 scripts/make_elsevier.py

# The KBS conformance checks live in the generator; the LaTeX static checks
# are shared with the Springer build.
check:
	cd .. && python3 scripts/make_elsevier.py
	cd .. && python3 scripts/check_latex.py --tex paper-kbs/$(MAIN).tex

# cas-dc.cls is Elsevier's and is not redistributed here.
$(MAIN).pdf: $(MAIN).tex paper.bib $(FIGS)
	@test -f cas-dc.cls || { \
	  echo "cas-dc.cls missing. Run: bash fetch-template.sh"; exit 1; }
	pdflatex -interaction=nonstopmode $(MAIN).tex
	bibtex $(MAIN) || true
	pdflatex -interaction=nonstopmode $(MAIN).tex
	pdflatex -interaction=nonstopmode $(MAIN).tex
	@echo "--- undefined citations/references ---"
	@grep -cE "Citation .* undefined|Reference .* undefined" $(MAIN).log || echo "  none"
	@echo "--- overfull hboxes (double column is tight) ---"
	@grep -c "Overfull \\\\hbox" $(MAIN).log || echo "  none"

# Elsevier wants editable sources; highlights go as a SEPARATE file.
zip:
	rm -f signalshap-kbs.zip
	zip -qr signalshap-kbs.zip $(MAIN).tex paper.bib highlights.tex figures/ \
	  $(wildcard cas-dc.cls) $(wildcard cas-common.sty) $(wildcard *.bst)
	@unzip -l signalshap-kbs.zip | tail -3

clean:
	rm -f *.aux *.bbl *.blg *.log *.out *.spl $(MAIN).pdf signalshap-kbs.zip
