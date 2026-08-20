#!/bin/bash
# Repaints every staff portrait with the freestyle watercolour treatment and
# rebuilds all derived sizes the site serves.
#   src of truth: assets/avatars-src/*.jpg (the original pale watercolours)
set -e
cd "$(dirname "$0")/.."
SRC=assets/avatars-src
[ -d "$SRC" ] || { echo "missing $SRC"; exit 1; }
mkdir -p assets/avatars assets/avatars-mobile assets/staff-cards \
         assets/staff-cards-webp assets/staff-cards-mobile-webp assets/staff-thumbs-mobile
i=0
for f in "$SRC"/*.jpg; do
  i=$((i+1)); n=$(basename "$f" .jpg); seed=$(( i * 17 + 11 ))
  tools/wc_paint.sh "$f" "/tmp/wcbig_$n.png" "$seed" 1024
  big="/tmp/wcbig_$n.png"
  convert "$big" -quality 86 -sampling-factor 4:2:0 -strip "assets/avatars/$n.jpg"
  convert "$big" -resize 480x480 -quality 84 -strip "assets/staff-cards/$n.jpg"
  convert "$big" -resize 480x480 -quality 80 -define webp:method=6 -strip "assets/staff-cards-webp/$n.webp"
  convert "$big" -resize 200x200 -quality 82 -strip "assets/avatars-mobile/$n.jpg"
  convert "$big" -resize 150x150 -quality 82 -strip "assets/staff-thumbs-mobile/$n.jpg"
  convert "$big" -resize 150x150 -quality 76 -define webp:method=6 -strip "assets/staff-cards-mobile-webp/$n.webp"
  rm -f "$big"
  printf '.'
done
echo " repainted $i portraits"
