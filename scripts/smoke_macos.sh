#!/usr/bin/env bash
# Tier-1 smoke tests for the macOS and iOS template artifacts.
# macOS: both universal binaries must run on the native runner and be fat
#        (x86_64 + arm64).
# iOS:   every static library injected into ios.zip must carry the right
#        architecture slice (arm64 device / x86_64 simulator).
#
# Usage: smoke_macos.sh <tag>   (e.g. "4.7.2-stable")
# Env:   ART_DIR base directory holding the downloaded artifacts
#        (subdirs: macos-release, macos-debug, ios; any may be absent).
set -euo pipefail

TAG="${1:?expected tag required, e.g. 4.7.2-stable}"
EXPECT_VER="${TAG%-stable}"
ART="${ART_DIR:-artifacts}"

fail() { echo "ERROR: $*" >&2; exit 1; }

# lipo_expect <file> <required arch>...
lipo_expect() {
  local file="$1" arch out
  [ -f "$file" ] || fail "missing file: $file"
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
  [ -f "$bin" ] || fail "missing macOS template binary: $bin"
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
if [ -f "$ART/macos-release/macos_out/godot_macos_release.universal" ]; then
  run_mac "$ART/macos-release/macos_out/godot_macos_release.universal"
fi
if [ -f "$ART/macos-debug/macos_out/godot_macos_debug.universal" ]; then
  run_mac "$ART/macos-debug/macos_out/godot_macos_debug.universal"
fi

# --- iOS: static libraries inside ios.zip ------------------------------------
if [ -f "$ART/ios/ios_out/ios.zip" ]; then
  tmp="$(mktemp -d)"
  unzip -q "$ART/ios/ios_out/ios.zip" -d "$tmp"
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
