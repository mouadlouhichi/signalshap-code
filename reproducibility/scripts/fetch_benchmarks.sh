#!/usr/bin/env bash
# Fetch the standard LightGCN benchmark splits (Gowalla, Yelp2018, Amazon-Book).
# These are the preprocessed splits distributed with LightGCN (He et al., SIGIR
# 2020), so our preprocessing matches published practice exactly.
set -euo pipefail
DEST="$(cd "$(dirname "$0")/.." && pwd)/data/raw"
mkdir -p "$DEST" && TMP=$(mktemp -d)
echo "fetching LightGCN benchmark data..."
curl -sL "https://codeload.github.com/kuandeng/LightGCN/tar.gz/refs/heads/master" | tar xz -C "$TMP"
for d in gowalla yelp2018 amazon-book; do
  cp -r "$TMP/LightGCN-master/Data/$d" "$DEST/" && echo "  $d -> $DEST/$d"
done
rm -rf "$TMP"

# MovieLens-1M. NOT redistributed with this repository: the GroupLens README
# states "The user may not redistribute the data without separate permission",
# so we fetch it from the original source instead of vendoring it.
if [ -f "$DEST/ml-1m/ratings.dat" ]; then
  echo "  ml-1m already present, skipping"
else
  echo "fetching MovieLens-1M from GroupLens..."
  TMP2=$(mktemp -d)
  curl -sL "https://files.grouplens.org/datasets/movielens/ml-1m.zip" -o "$TMP2/ml-1m.zip"
  unzip -q "$TMP2/ml-1m.zip" -d "$TMP2"
  mkdir -p "$DEST/ml-1m"
  cp "$TMP2/ml-1m/"*.dat "$TMP2/ml-1m/README" "$DEST/ml-1m/"
  rm -rf "$TMP2"
  echo "  ml-1m -> $DEST/ml-1m (subject to the GroupLens terms in its README)"
fi
echo "done."
