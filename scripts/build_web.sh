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

EXPECTED_ZIPS=(
  godot.web.template_release.wasm32.zip
  godot.web.template_release.wasm32.nothreads.zip
  godot.web.template_release.wasm32.dlink.zip
  godot.web.template_release.wasm32.nothreads.dlink.zip
  godot.web.template_debug.wasm32.zip
  godot.web.template_debug.wasm32.nothreads.zip
  godot.web.template_debug.wasm32.dlink.zip
  godot.web.template_debug.wasm32.nothreads.dlink.zip
)

for variant in "${VARIANTS[@]}"; do
  variant_tag="${variant// /_}"
  echo "=== Web wave: $variant ==="
  pids=()
  for target in template_release template_debug; do
    dir="$WORK/${variant_tag}_${target}"
    cp -r "$SRC" "$dir"
    (
      cd "$dir"
      scons platform=web "target=$target" arch=wasm32 production=yes use_closure_compiler=yes \
        progress=no -j"$JOBS" $variant $EXTRA_ARGS
      cp bin/godot.web.*.zip "$SRC/bin/"
    ) &
    pids+=("$!")
  done
  # set -e does not see background job failures; wait on each PID explicitly.
  wave_failed=0
  for pid in "${pids[@]}"; do
    wait "$pid" || wave_failed=1
  done
  if [ "$wave_failed" -ne 0 ]; then
    echo "ERROR: web wave failed: $variant" >&2
    exit 1
  fi
  echo "=== Web wave done: $variant ==="
done

echo "Web template zips:"
for name in "${EXPECTED_ZIPS[@]}"; do
  if [ ! -f "$SRC/bin/$name" ]; then
    echo "ERROR: web build did not produce $name" >&2
    exit 1
  fi
done
ls -l "$SRC/bin/"
