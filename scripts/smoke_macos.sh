#!/usr/bin/env bash
# Tier-1 smoke tests for the macOS and iOS template artifacts.
# macOS: both universal binaries must run on the native runner and be fat
#        (x86_64 + arm64).
# iOS:   every static library injected into ios.zip must carry the right
#        architecture slice (arm64 device / x86_64 simulator).
#
# Usage: smoke_macos.sh <tag>   (e.g. "4.7.2-stable")
#
# Expectation env vars set by the workflow ("true" = the platform was built,
# its artifacts MUST be present and are checked; anything else = skip):
#   EXPECT_MACOS_RELEASE, EXPECT_MACOS_DEBUG, EXPECT_IOS
# Env:   ART_DIR base directory holding the downloaded artifacts. Artifact
#        contents live flat at the top level: upload-artifact v4 strips the
#        common ancestor of the upload globs (e.g. "macos_out/", "ios_out/").
set -euo pipefail

TAG="${1:?expected tag required, e.g. 4.7.2-stable}"
EXPECT_VER="${TAG%-stable}"
ART="${ART_DIR:-artifacts}"

fail() { echo "ERROR: $*" >&2; exit 1; }

want() { [ "${!1:-}" = "true" ]; }

require_file() { [ -f "$1" ] || fail "missing expected artifact file: $1"; }

# lipo_expect <file> <required arch>...
lipo_expect() {
  local file="$1" arch out
  require_file "$file"
  out="$(lipo -info "$file")" || fail "lipo failed on $file"
  shift
  for arch in "$@"; do
    printf '%s\n' "$out" | grep -qw "$arch" \
      || fail "$file: missing architecture $arch (lipo: $out)"
  done
  echo "OK: $file (${out##*: })"
}

run_mac() {
  local bin="$1" out
  require_file "$bin"
  chmod +x "$bin"
  if ! out="$("$bin" --headless --version 2>&1)"; then
    fail "$bin exited non-zero"
  fi
  printf '%s\n' "$out" | head -n1
  printf '%s\n' "$out" | grep -q "^Godot Engine v$EXPECT_VER" \
    || fail "$bin: unexpected --version output: $out"
  lipo_expect "$bin" x86_64 arm64
  echo "OK: $bin"
}

# --- macOS: run both universal binaries --------------------------------------
if want EXPECT_MACOS_RELEASE; then
  run_mac "$ART/macos-release/godot_macos_release.universal"
fi
if want EXPECT_MACOS_DEBUG; then
  run_mac "$ART/macos-debug/godot_macos_debug.universal"
fi

# --- iOS: static libraries inside ios.zip ------------------------------------
if want EXPECT_IOS; then
  require_file "$ART/ios/ios.zip"
  tmp="$(mktemp -d)"
  unzip -q "$ART/ios/ios.zip" -d "$tmp"
  lipo_expect "$tmp/libgodot.ios.release.xcframework/ios-arm64/libgodot.a" arm64
  lipo_expect "$tmp/libgodot.ios.release.xcframework/ios-arm64_x86_64-simulator/libgodot.a" x86_64
  lipo_expect "$tmp/libgodot.ios.debug.xcframework/ios-arm64/libgodot.a" arm64
  lipo_expect "$tmp/libgodot.ios.debug.xcframework/ios-arm64_x86_64-simulator/libgodot.a" x86_64
  lipo_expect "$tmp/libgodot_camera.ios.release.xcframework/ios-arm64/libgodot_camera.a" arm64
  lipo_expect "$tmp/libgodot_camera.ios.release.xcframework/ios-arm64_x86_64-simulator/libgodot_camera.a" x86_64
  lipo_expect "$tmp/libgodot_camera.ios.debug.xcframework/ios-arm64/libgodot_camera.a" arm64
  lipo_expect "$tmp/libgodot_camera.ios.debug.xcframework/ios-arm64_x86_64-simulator/libgodot_camera.a" x86_64
  rm -rf "$tmp"
fi

echo "macOS/iOS smoke tests passed."
