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
# Last.fm-1K: the UPF host now returns 403 to non-browser clients. Try a few
# mirrors, then fall back to printing manual instructions rather than failing
# silently -- two timestamped corpora are already enough for the five-source
# game, so this one is optional.
if [ -d "$DEST/lastfm_1k" ]; then
  echo "  Last.fm-1K: already present"
else
  LFM_OK=0
  for u in \
    "https://web.archive.org/web/2019/http://mtg.upf.edu/static/datasets/last.fm/lastfm-dataset-1K.tar.gz" \
    "http://ocelma.net/MusicRecommendationDataset/lastfm-1K.tar.gz" ; do
    echo "  Last.fm-1K: trying $(echo "$u" | cut -d/ -f3)..."
    tmp=$(mktemp -d)
    if curl -fsSL --retry 2 --max-time 900 -A "Mozilla/5.0" -o "$tmp/f" "$u" 2>/dev/null \
       && tar tzf "$tmp/f" >/dev/null 2>&1; then
      mkdir -p "$DEST/lastfm_1k" && tar xzf "$tmp/f" -C "$DEST/lastfm_1k"
      echo "  Last.fm-1K: -> $DEST/lastfm_1k"; LFM_OK=1; rm -rf "$tmp"; break
    fi
    rm -rf "$tmp"
  done
  if [ "$LFM_OK" -eq 0 ]; then
    echo "  Last.fm-1K: UNAVAILABLE (upstream host returns 403)."
    echo "     OPTIONAL -- Gowalla and Amazon already give you two timestamped"
    echo "     corpora plus MovieLens-1M, which is enough for the five-source game."
    echo "     To add it anyway, download lastfm-dataset-1K.tar.gz in a browser"
    echo "     from http://ocelma.net/MusicRecommendationDataset/ and extract to:"
    echo "       $DEST/lastfm_1k/"
  fi
fi
get "Amazon Video Games" "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/review_categories/Video_Games.jsonl.gz" "amazon_Video_Games"

echo
echo "MovieLens-1M already carries timestamps; place it at data/raw/ml-1m/"
echo
echo "Verify before running the game:"
echo "  python -c \"import sys;sys.path.insert(0,'src');\\"
echo "from signalshap.data.timestamped import load_gowalla_timestamped, temporal_validity_report as v;\\"
echo "print(v(load_gowalla_timestamped(max_users=3000)))\""
