# Knowledge and Information Systems (Springer, journal 10115) build.
#
# kais-article.tex is GENERATED from ../paper-kbs/kbs-article.tex by
# ../scripts/make_kais.py. The KBS file is the latest manuscript and is the
# source of truth for prose and numbers; check_paper_numbers.py validates the
# Springer original against artefacts/, and tests/test_kais_port.py asserts
# that the KAIS body is the KBS body modulo the single-column float demotion.
#
#   make regen    rebuild kais-article.tex from the KBS manuscript
#   make          checks, then the PDF
#   make zip      flat submission bundle
#   make clean    remove build products
.PHONY: all regen check zip clean
MAIN = kais-article
FIGS = $(wildcard figures/*.png)

all: check $(MAIN).pdf

regen:
	cd .. && python3 scripts/make_kais.py

check:
	cd .. && python3 scripts/check_latex.py --tex paper-kais/$(MAIN).tex \
	  --cls paper-kais/sn-jnl.cls
	cd .. && python3 scripts/check_paper_numbers.py

# Unlike Elsevier's cas-dc.cls, sn-jnl.cls and sn-basic.bst are LPPL and ship
# in this directory, so the build needs no fetch step.
$(MAIN).pdf: $(MAIN).tex paper.bib $(FIGS) sn-jnl.cls sn-basic.bst
	pdflatex -interaction=nonstopmode $(MAIN).tex
	bibtex $(MAIN) || true
	pdflatex -interaction=nonstopmode $(MAIN).tex
	pdflatex -interaction=nonstopmode $(MAIN).tex
	@echo "--- undefined citations/references ---"
	@grep -cE "Citation .* undefined|Reference .* undefined" $(MAIN).log || echo "  none"
	@echo "--- overfull hboxes ---"
	@grep -c "Overfull \\\\hbox" $(MAIN).log || echo "  none"

# Springer asks for the original source including all style files and figures,
# plus a PDF of the compiled output uploaded as its own item. Build products
# are excluded: shipping a previous run's .bbl invites it being compiled
# instead of a fresh bibtex pass.
zip: check
	rm -f signalshap-kais.zip
	zip -qr signalshap-kais.zip $(MAIN).tex paper.bib figures/ \
	  sn-jnl.cls sn-basic.bst
	@echo "--- contents ---"
	@unzip -l signalshap-kais.zip
	@if unzip -l signalshap-kais.zip | grep -qE "\.(aux|log|bbl|blg|fls|fdb_latexmk|out|synctex)"; then \
	  echo "ERROR: build products leaked into the bundle"; exit 1; fi
	@echo "clean: editable sources only"

clean:
	rm -f *.aux *.bbl *.blg *.log *.out *.spl $(MAIN).pdf signalshap-kais.zip
