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
echo "done. MovieLens-1M must be placed at data/raw/ml-1m/ separately."
