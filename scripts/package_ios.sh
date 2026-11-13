#!/usr/bin/env bash
# Assemble ios.zip the same way the official release pipeline does:
# the Xcode project template from misc/dist/apple_embedded_xcode with the built
# static libraries injected into the xcframeworks, plus MoltenVK.xcframework
# (from the LunarG Vulkan SDK, if installed) and AccessKit.xcframework (if built).
#
# Usage: package_ios.sh <godot-checkout-dir>
# Env:   IOS_OUT_DIR output dir for ios.zip (default: ios_out)
set -euo pipefail

GODOT_DIR="${1:?godot checkout dir required}"
cd "$GODOT_DIR"

OUT_DIR="${IOS_OUT_DIR:-ios_out}"
mkdir -p "$OUT_DIR"

warn() { echo "WARNING: $*" >&2; }

REQUIRED_LIBS=(
  libgodot.ios.template_release.arm64.a
  libgodot.ios.template_debug.arm64.a
  libgodot_camera.ios.template_release.arm64.a
  libgodot_camera.ios.template_debug.arm64.a
  libgodot.ios.template_release.x86_64.simulator.a
  libgodot.ios.template_debug.x86_64.simulator.a
  libgodot_camera.ios.template_release.x86_64.simulator.a
  libgodot_camera.ios.template_debug.x86_64.simulator.a
)
for lib in "${REQUIRED_LIBS[@]}"; do
  if [ ! -f "bin/$lib" ]; then
    echo "ERROR: missing built library bin/$lib" >&2
    exit 1
  fi
done

rm -rf .build/ios_xcode
mkdir -p .build
cp -r misc/dist/apple_embedded_xcode .build/ios_xcode

# Inject the built libraries into the xcframeworks (exact mapping from the
# official godot-build-scripts packaging).
cp bin/libgodot.ios.template_release.arm64.a          .build/ios_xcode/libgodot.ios.release.xcframework/ios-arm64/libgodot.a
cp bin/libgodot.ios.template_debug.arm64.a            .build/ios_xcode/libgodot.ios.debug.xcframework/ios-arm64/libgodot.a
cp bin/libgodot.ios.template_release.x86_64.simulator.a  .build/ios_xcode/libgodot.ios.release.xcframework/ios-arm64_x86_64-simulator/libgodot.a
cp bin/libgodot.ios.template_debug.x86_64.simulator.a    .build/ios_xcode/libgodot.ios.debug.xcframework/ios-arm64_x86_64-simulator/libgodot.a
cp bin/libgodot_camera.ios.template_release.arm64.a   .build/ios_xcode/libgodot_camera.ios.release.xcframework/ios-arm64/libgodot_camera.a
cp bin/libgodot_camera.ios.template_debug.arm64.a     .build/ios_xcode/libgodot_camera.ios.debug.xcframework/ios-arm64/libgodot_camera.a
cp bin/libgodot_camera.ios.template_release.x86_64.simulator.a  .build/ios_xcode/libgodot_camera.ios.release.xcframework/ios-arm64_x86_64-simulator/libgodot_camera.a
cp bin/libgodot_camera.ios.template_debug.x86_64.simulator.a    .build/ios_xcode/libgodot_camera.ios.debug.xcframework/ios-arm64_x86_64-simulator/libgodot_camera.a

rm -rf .build/ios_xcode/libgodot.visionos.*

MOLTENVK="$(find "$HOME/VulkanSDK" -maxdepth 4 -type d -name MoltenVK.xcframework 2>/dev/null | head -n 1 || true)"
if [ -n "$MOLTENVK" ]; then
  cp -R "$MOLTENVK" .build/ios_xcode/
  rm -rf .build/ios_xcode/MoltenVK.xcframework/{macos,tvos,xros}* 2>/dev/null || true
  echo "Injected MoltenVK.xcframework from: $MOLTENVK"
else
  warn "MoltenVK.xcframework not found (Vulkan SDK not installed?) - ios.zip will lack Vulkan support."
fi

ACCESSKIT="$(find bin/build_deps -maxdepth 6 -type d -name AccessKit.xcframework 2>/dev/null | head -n 1 || true)"
if [ -n "$ACCESSKIT" ]; then
  cp -R "$ACCESSKIT" .build/ios_xcode/
  echo "Injected AccessKit.xcframework from: $ACCESSKIT"
else
  warn "AccessKit.xcframework not found - accessibility support will be omitted."
fi

# OUT_DIR may be absolute (CI passes $GITHUB_WORKSPACE/ios_out); only prefix
# relative paths with the current (godot) dir.
case "$OUT_DIR" in
  /*) ABS_OUT="$OUT_DIR" ;;
  *)  ABS_OUT="$(pwd)/$OUT_DIR" ;;
esac
( cd .build/ios_xcode && zip -q -9 -r "$ABS_OUT/ios.zip" . )
rm -rf .build/ios_xcode

echo "Created $OUT_DIR/ios.zip ($(du -h "$OUT_DIR/ios.zip" | cut -f1))"
