#!/usr/bin/env bash
# Tier-1 smoke tests for the Linux, Web and Android template artifacts.
# Linux: the template binaries must actually start on a native runner and
#        report the pinned engine version (catches broken links / packaging).
# Web:   every template zip must carry a .wasm payload.
# Android: both APKs must contain a libgodot .so for every supported ABI.
#
# Usage: smoke_linux.sh <tag>   (e.g. "4.7.2-stable")
#
# Expectation env vars set by the workflow ("true" = the platform was built,
# its artifacts MUST be present and are checked; anything else = skip):
#   EXPECT_LINUX_RELEASE, EXPECT_LINUX_DEBUG, EXPECT_WEB, EXPECT_ANDROID
# Env:   ART_DIR base directory holding the downloaded artifacts. Artifact
#        contents live flat at the top level: upload-artifact v4 strips the
#        common ancestor of the upload globs (e.g. "godot/bin/").
set -euo pipefail

TAG="${1:?expected tag required, e.g. 4.7.2-stable}"
EXPECT_VER="${TAG%-stable}"
ART="${ART_DIR:-artifacts}"

fail() { echo "ERROR: $*" >&2; exit 1; }

# want <VAR_NAME>: is the platform expected in this run?
want() { [ "${!1:-}" = "true" ]; }

require_file() { [ -f "$1" ] || fail "missing expected artifact file: $1"; }

# --- Linux: run the template binaries ----------------------------------------
run_linux() {
  local bin="$1" out
  require_file "$bin"
  chmod +x "$bin"
  if ! out="$("$bin" --headless --version 2>&1)"; then
    fail "$bin exited non-zero"
  fi
  printf '%s\n' "$out" | head -n1
  printf '%s\n' "$out" | grep -q "^Godot Engine v$EXPECT_VER" \
    || fail "$bin: unexpected --version output: $out"
  echo "OK: $bin"
}

if want EXPECT_LINUX_RELEASE; then
  run_linux "$ART/linux-release/godot.linuxbsd.template_release.x86_64"
fi
if want EXPECT_LINUX_DEBUG; then
  run_linux "$ART/linux-debug/godot.linuxbsd.template_debug.x86_64"
fi

# --- Web: every zip must contain a wasm payload ------------------------------
if want EXPECT_WEB; then
  count=0
  for zip in "$ART/web/"godot.web.template_*.wasm32*.zip; do
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
  require_file "$apk"
  for abi in arm64-v8a armeabi-v7a x86_64; do
    unzip -l "$apk" | grep -q "lib/$abi/libgodot.*\.so" \
      || fail "$apk: no libgodot .so for $abi"
  done
  echo "OK: $apk"
}

if want EXPECT_ANDROID; then
  check_apk "$ART/android/android_release.apk"
  check_apk "$ART/android/android_debug.apk"
  require_file "$ART/android/android_source.zip"
  echo "OK: android_source.zip"
fi

echo "Linux/Web/Android smoke tests passed."
