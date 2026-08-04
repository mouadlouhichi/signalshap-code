#!/usr/bin/env bash
# Fetch corpora that carry REAL timestamps.
#
# Three of five players (rec, seq, and the decay term of pop) are meaningless
# without interaction times. The LightGCN benchmark splits discard them, so
# these are the corpora needed for a defensible five-source game.
#
# Run from a machine with open network access; several hosts are unreachable
# from restricted CI environments.
set -uo pipefail
DEST="$(cd "$(dirname "$0")/.." && pwd)/data/raw"
mkdir -p "$DEST"

get() {  # name url subdir
  local name=$1 url=$2 sub=$3
  if [ -d "$DEST/$sub" ]; then echo "  $name: already present"; return; fi
  echo "  $name: downloading..."
  local tmp; tmp=$(mktemp -d)
  if ! curl -fsSL --retry 3 --max-time 1800 -o "$tmp/f" "$url"; then
    echo "  $name: DOWNLOAD FAILED -- fetch manually from $url"; rm -rf "$tmp"; return
  fi
  mkdir -p "$DEST/$sub"
  case "$url" in
    *.zip)    unzip -qo "$tmp/f" -d "$DEST/$sub" ;;
    *.tar.gz) tar xzf "$tmp/f" -C "$DEST/$sub" ;;
    *.gz)     gunzip -c "$tmp/f" > "$DEST/$sub/$(basename "${url%.gz}")" ;;
    *)        mv "$tmp/f" "$DEST/$sub/$(basename "$url")" ;;
  esac
  rm -rf "$tmp"; echo "  $name: -> $DEST/$sub"
}

echo "Timestamped corpora"
get "Gowalla check-ins"  "https://snap.stanford.edu/data/loc-gowalla_totalCheckins.txt.gz" "gowalla_ts"
get "Last.fm-1K"         "http://mtg.upf.edu/static/datasets/last.fm/lastfm-dataset-1K.tar.gz" "lastfm_1k"
get "Amazon Video Games" "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/review_categories/Video_Games.jsonl.gz" "amazon_Video_Games"

echo
echo "MovieLens-1M already carries timestamps; place it at data/raw/ml-1m/"
echo
echo "Verify before running the game:"
echo "  python -c \"import sys;sys.path.insert(0,'src');\\"
echo "from signalshap.data.timestamped import load_gowalla_timestamped, temporal_validity_report as v;\\"
echo "print(v(load_gowalla_timestamped(max_users=3000)))\""
