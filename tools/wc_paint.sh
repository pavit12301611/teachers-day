#!/bin/bash
# ---------------------------------------------------------------------------
# Freestyle watercolour enhancer
# Takes the pale watercolour staff portrait and repaints it as a vivid,
# colour-splashed painting: rainbow washes bleeding through the paper areas,
# loose paint splashes hugging the edges, faint pencil lines and paper grain.
# Deterministic: same seed -> same painting.
#   usage: tools/wc_paint.sh <src> <out> <seed> [size]
# ---------------------------------------------------------------------------
set -e
src="$1"; out="$2"; seed="${3:-7}"; size="${4:-1024}"
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
h1=$(( (seed * 47) % 300 ))
h2=$(( (seed * 83) % 300 ))
bw=$(( size / 22 )); [ $bw -lt 4 ] && bw=4
mb=$(( size / 96 )); [ $mb -lt 2 ] && mb=2

convert "$src" -resize ${size}x${size}\! -modulate 101,130,100 "$t/base.png"

# 1. rainbow wash, kept to the pale "paper" pixels so faces stay natural
convert -size 256x256 -seed $seed plasma:fractal -blur 0x6 \
        -modulate 112,190,$h1 -fill white -colorize 44% -resize ${size}x${size}\! "$t/wash.png"
convert "$t/base.png" -colorspace gray -level 46%,96% "$t/lum.png"
convert "$t/base.png" -colorspace HSL -channel G -separate +channel -negate -level 8%,62% "$t/sat.png"
convert -size 256x256 radial-gradient:black-white -fill white -colorize 42% -resize ${size}x${size}\! "$t/soften.png"
convert "$t/lum.png" "$t/sat.png" -compose multiply -composite \
        "$t/soften.png" -compose multiply -composite -resize 25% -blur 0x2 -resize 400% "$t/mask.png"
convert "$t/base.png" "$t/wash.png" -compose multiply -composite "$t/washed.png"
convert "$t/base.png" "$t/washed.png" "$t/mask.png" -compose over -composite "$t/s1.png"

# 2. loose freestyle splashes around the border
convert -size 256x256 -seed $((seed+91)) plasma:fractal -blur 0x3 \
        -auto-level -level 55%,90% -resize ${size}x${size}\! "$t/blobs.png"
convert -size 256x256 radial-gradient:black-white -level 25%,100% -resize ${size}x${size}\! "$t/ring.png"
convert "$t/blobs.png" "$t/ring.png" -compose multiply -composite -colorspace gray -resize 25% -blur 0x2 -resize 400% "$t/splmask.png"
convert -size 256x256 -seed $((seed+55)) plasma:fractal -blur 0x8 \
        -modulate 108,240,$h2 -fill white -colorize 25% -resize ${size}x${size}\! "$t/splcolor.png"
convert "$t/s1.png" \( "$t/s1.png" "$t/splcolor.png" -compose multiply -composite \) \
        "$t/splmask.png" -compose over -composite "$t/s2.png"

# 3. faint pencil lines -> reads as hand-drawn
convert "$t/base.png" -colorspace gray -negate -blur 0x1.2 -negate \
        \( +clone -blur 0x$((size/160+1)) \) -compose divide -composite \
        -level 0%,92% -negate -level 0%,26% -negate -blur 0x0.5 "$t/ink.png"
convert "$t/s2.png" "$t/ink.png" -compose multiply -composite "$t/s3.png"

# 4. cold-press paper grain + final punch
convert -size ${size}x${size} -seed $((seed+3)) xc: +noise Gaussian -colorspace gray -blur 0x0.7 -auto-level "$t/grain.png"
convert "$t/s3.png" "$t/grain.png" -compose blend -define compose:args=9 -composite \
        -modulate 101,112,100 -sigmoidal-contrast 2,50% -unsharp 0x0.8+0.4+0.02 "$out"
