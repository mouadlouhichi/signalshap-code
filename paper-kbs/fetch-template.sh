#!/usr/bin/env bash
# Fetch the Elsevier CAS LaTeX bundle (cas-dc.cls and friends).
#
# The class files are Elsevier's and are NOT redistributed in this repository.
# Run this once before building paper-kbs/.
set -uo pipefail
DEST="$(cd "$(dirname "$0")" && pwd)"
TMP=$(mktemp -d)

URL="https://assets.ctfassets.net/o78em1y1w4i4/5uFmLZJTPDMAUjFnHRpjj8/6f19a979146eb93263763d87a894ab0d/els-cas-templates.zip"
echo "fetching Elsevier CAS templates..."
if ! curl -fsSL --retry 3 --max-time 600 -o "$TMP/cas.zip" "$URL"; then
  echo "DOWNLOAD FAILED. Fetch it manually from"
  echo "  https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions"
  echo "and copy cas-dc.cls, cas-common.sty and elsarticle-num.bst into $DEST"
  rm -rf "$TMP"; exit 1
fi

unzip -qo "$TMP/cas.zip" -d "$TMP/x"
for f in cas-dc.cls cas-sc.cls cas-common.sty; do
  found=$(find "$TMP/x" -name "$f" | head -1)
  [ -n "$found" ] && cp "$found" "$DEST/" && echo "  $f"
done
# Numbered bibliography style. CAS ships cas-model2-names; elsarticle-num is
# the numbered style the KBS guide's [n] citation format needs.
for f in elsarticle-num.bst cas-model2-names.bst; do
  found=$(find "$TMP/x" -name "$f" | head -1)
  [ -n "$found" ] && cp "$found" "$DEST/" && echo "  $f"
done
rm -rf "$TMP"

if [ ! -f "$DEST/elsarticle-num.bst" ]; then
  echo "NOTE: elsarticle-num.bst was not in the CAS bundle."
  echo "      Get it from CTAN: https://ctan.org/pkg/elsarticle"
fi
echo "done."
