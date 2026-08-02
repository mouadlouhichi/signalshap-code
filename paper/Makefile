# Build the manuscript. Requires a TeX distribution (texlive-latex-recommended,
# texlive-fonts-recommended, texlive-bibtex-extra).
#
# Regenerate assets first if results changed:
#   (cd .. && python scripts/run_study.py --synthetic && python scripts/make_assets.py)
.PHONY: all clean
all: paper.pdf
paper.pdf: paper.tex paper.bib
	pdflatex -interaction=nonstopmode paper.tex
	bibtex paper || true
	pdflatex -interaction=nonstopmode paper.tex
	pdflatex -interaction=nonstopmode paper.tex
clean:
	rm -f *.aux *.bbl *.blg *.log *.out *.toc paper.pdf
