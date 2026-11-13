#!/usr/bin/env bash
# Tier-1 smoke tests for the Windows template artifacts.
# Both targets and both wrappers (main GUI exe + console exe) must exit 0 on a
# native runner; the console wrappers must additionally print the version
# banner of the pinned engine version (the GUI exe may not write to stdout
# depending on how it was launched, so its output is not asserted).
#
# Usage: smoke_windows.sh <tag>   (e.g. "4.7.2-stable")
# Env:   ART_DIR base directory holding the downloaded artifacts
#        (subdirs: windows-release, windows-debug; any may be absent).
set -euo pipefail

TAG="${1:?expected tag required, e.g. 4.7.2-stable}"
EXPECT_VER="${TAG%-stable}"
ART="${ART_DIR:-artifacts}"

fail() { echo "ERROR: $*" >&2; exit 1; }

# run_win <exe> <yes|no expect version on stdout>
run_win() {
  local exe="$1" want_output="$2" out
  [ -f "$exe" ] || fail "missing Windows template binary: $exe"
  if ! out="$("$exe" --headless --version 2>&1)"; then
    fail "$exe exited non-zero"
  fi
  if [ "$want_output" = "yes" ] && ! printf '%s' "$out" | grep -q "^Godot Engine v$EXPECT_VER"; then
    fail "$exe: unexpected --version output: $out"
  fi
  if [ -n "$out" ]; then
    printf '%s\n' "$out" | head -n1
  fi
  echo "OK: $exe"
}

if [ -f "$ART/windows-release/godot/bin/godot.windows.template_release.x86_64.exe" ]; then
  run_win "$ART/windows-release/godot/bin/godot.windows.template_release.x86_64.exe" no
  run_win "$ART/windows-release/godot/bin/godot.windows.template_release.x86_64_console.exe" yes
fi
if [ -f "$ART/windows-debug/godot/bin/godot.windows.template_debug.x86_64.exe" ]; then
  run_win "$ART/windows-debug/godot/bin/godot.windows.template_debug.x86_64.exe" no
  run_win "$ART/windows-debug/godot/bin/godot.windows.template_debug.x86_64_console.exe" yes
fi

echo "Windows smoke tests passed."
