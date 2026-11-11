#!/usr/bin/env bash
# Build all eight web template variants, matching the official release pipeline:
#   target=template_release|template_debug  x  threads=yes|no  x  dlink_enabled=yes|no
# The built zips land in <godot>/bin/ as godot.web.template_<target>.wasm32*.zip.
#
# emscripten LTO linking (production=yes) is memory-hungry, so builds run in waves
# of two parallel source copies with SCONS_JOBS cores each.
#
# Usage: build_web.sh <godot-checkout-dir>
# Env:   SCONS_JOBS       scons -j value per build (default 2)
#        SCONS_EXTRA_ARGS extra scons args (e.g. build_profile=/abs/path, vulkan=no)
set -euo pipefail

GODOT_DIR="${1:?godot checkout dir required}"
JOBS="${SCONS_JOBS:-2}"
EXTRA_ARGS="${SCONS_EXTRA_ARGS:-}"

VARIANTS=(
  "threads=yes dlink_enabled=no"
  "threads=no dlink_enabled=no"
  "threads=yes dlink_enabled=yes"
  "threads=no dlink_enabled=yes"
)

SRC="$(cd "$GODOT_DIR" && pwd)"
mkdir -p "$SRC/bin"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

for variant in "${VARIANTS[@]}"; do
  variant_tag="${variant// /_}"
  echo "=== Web wave: $variant ==="
  for target in template_release template_debug; do
    dir="$WORK/${variant_tag}_${target}"
    cp -r "$SRC" "$dir"
    (
      cd "$dir"
      scons platform=web "target=$target" arch=wasm32 production=yes use_closure_compiler=yes \
        progress=no -j"$JOBS" $variant $EXTRA_ARGS
      cp bin/godot.web.*.zip "$SRC/bin/"
    ) &
  done
  wait
  echo "=== Web wave done: $variant ==="
done

echo "Web template zips:"
ls -l "$SRC/bin/"
