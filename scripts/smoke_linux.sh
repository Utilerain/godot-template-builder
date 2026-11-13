#!/usr/bin/env bash
# Tier-1 smoke tests for the Linux, Web and Android template artifacts.
# Linux: the template binaries must actually start on a native runner and
#        report the pinned engine version (catches broken links / packaging).
# Web:   every template zip must carry a .wasm payload.
# Android: both APKs must contain a libgodot .so for every supported ABI.
#
# Usage: smoke_linux.sh <tag>   (e.g. "4.7.2-stable")
# Env:   ART_DIR base directory holding the downloaded artifacts
#        (subdirs: linux-release, linux-debug, web, android; any may be absent,
#        each block is skipped when its artifacts were not built).
set -euo pipefail

TAG="${1:?expected tag required, e.g. 4.7.2-stable}"
EXPECT_VER="${TAG%-stable}"
ART="${ART_DIR:-artifacts}"

fail() { echo "ERROR: $*" >&2; exit 1; }

# --- Linux: run the template binaries ----------------------------------------
run_linux() {
  local bin="$1" out
  [ -f "$bin" ] || fail "missing Linux template binary: $bin"
  chmod +x "$bin"
  if ! out="$("$bin" --headless --version 2>&1)"; then
    fail "$bin exited non-zero"
  fi
  printf '%s\n' "$out" | head -n1
  printf '%s\n' "$out" | grep -q "^Godot Engine v$EXPECT_VER" \
    || fail "$bin: unexpected --version output: $out"
  echo "OK: $bin"
}

if [ -f "$ART/linux-release/godot/bin/godot.linuxbsd.template_release.x86_64" ]; then
  run_linux "$ART/linux-release/godot/bin/godot.linuxbsd.template_release.x86_64"
fi
if [ -f "$ART/linux-debug/godot/bin/godot.linuxbsd.template_debug.x86_64" ]; then
  run_linux "$ART/linux-debug/godot/bin/godot.linuxbsd.template_debug.x86_64"
fi

# --- Web: every zip must contain a wasm payload ------------------------------
if [ -d "$ART/web" ]; then
  count=0
  for zip in "$ART/web/godot/bin/"godot.web.template_*.wasm32*.zip; do
    [ -f "$zip" ] || continue
    count=$((count + 1))
    unzip -l "$zip" | grep -q '\.wasm$' || fail "$(basename "$zip"): no .wasm payload"
    echo "OK: $(basename "$zip")"
  done
  [ "$count" -eq 8 ] || fail "expected 8 web template zips, found $count"
fi

# --- Android: APKs must carry libgodot .so for every supported ABI -----------
check_apk() {
  local apk="$1" abi
  [ -f "$apk" ] || fail "missing Android template APK: $apk"
  for abi in arm64-v8a armeabi-v7a x86_64; do
    unzip -l "$apk" | grep -q "lib/$abi/libgodot.*\.so" \
      || fail "$apk: no libgodot .so for $abi"
  done
  echo "OK: $apk"
}

if [ -d "$ART/android" ]; then
  check_apk "$ART/android/android_release.apk"
  check_apk "$ART/android/android_debug.apk"
  [ -f "$ART/android/android_source.zip" ] || fail "missing android_source.zip"
  echo "OK: android_source.zip"
fi

echo "Linux/Web/Android smoke tests passed."
