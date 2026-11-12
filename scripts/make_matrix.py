#!/usr/bin/env python3
"""Build the dynamic build matrix for the build workflow from the selected platforms.

Each platform group maps to a workflow_dispatch boolean input. The output is a
JSON matrix ({"include": [...]}) written to GITHUB_OUTPUT for consumption via
fromJson().

The `dotnet` group builds the same platforms a second time with the mono/.NET
module enabled (artifact dirs `template-net-*`), producing the separate
`*_mono_export_templates.tpz` package. Web is not supported for .NET builds.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

GROUPS = ("windows", "linux", "web", "android", "ios", "macos", "dotnet")

# Runner images are pinned, not "-latest": GitHub rolls the -latest label to a
# new OS release (ubuntu-latest moved 24.04 -> 26.04 around 2026-11-12, and the
# 26.04 toolchain broke the embree link of the mono editor). Runner choices
# follow the official Godot CI for 4.x: native Linux builds on ubuntu-22.04
# ("stay one LTS before latest" — also keeps the glibc requirement of the
# shipped templates low), android/web on ubuntu-24.04, windows on windows-latest
# (same label the official Windows CI uses).
RUNNER_LINUX = "ubuntu-22.04"
RUNNER_UBUNTU = "ubuntu-24.04"
RUNNER_WINDOWS = "windows-latest"
RUNNER_MACOS = "macos-26"

NO_MONO = "module_mono_enabled=no"
YES_MONO = "module_mono_enabled=yes"

ENTRIES = [
    # Standard builds
    {
        "group": "windows",
        "key": "windows-release",
        "os": RUNNER_WINDOWS,
        "platform": "windows",
        "target": "template_release",
        "variant": "standard",
        "mono_flag": NO_MONO,
        "bin_suffix": "",
        "scons_extra": "",
        "artifact_glob": "godot/bin/godot.windows.template_release.x86_64*.exe",
        "timeout": 240,
    },
    {
        "group": "windows",
        "key": "windows-debug",
        "os": RUNNER_WINDOWS,
        "platform": "windows",
        "target": "template_debug",
        "variant": "standard",
        "mono_flag": NO_MONO,
        "bin_suffix": "",
        "scons_extra": "",
        "artifact_glob": "godot/bin/godot.windows.template_debug.x86_64*.exe",
        "timeout": 240,
    },
    {
        "group": "linux",
        "key": "linux-release",
        "os": RUNNER_LINUX,
        "platform": "linux",
        "target": "template_release",
        "variant": "standard",
        "mono_flag": NO_MONO,
        "bin_suffix": "",
        "scons_extra": "use_static_cpp=yes",
        "artifact_glob": "godot/bin/godot.linuxbsd.template_release.x86_64",
        "timeout": 180,
    },
    {
        "group": "linux",
        "key": "linux-debug",
        "os": RUNNER_LINUX,
        "platform": "linux",
        "target": "template_debug",
        "variant": "standard",
        "mono_flag": NO_MONO,
        "bin_suffix": "",
        "scons_extra": "use_static_cpp=yes",
        "artifact_glob": "godot/bin/godot.linuxbsd.template_debug.x86_64",
        "timeout": 180,
    },
    {
        "group": "web",
        "key": "web",
        "os": RUNNER_UBUNTU,
        "platform": "web",
        "target": "template_release",
        "variant": "standard",
        "mono_flag": NO_MONO,
        "bin_suffix": "",
        "scons_extra": "",
        "artifact_glob": "godot/bin/godot.web.template_*.wasm32*.zip",
        "timeout": 300,
    },
    {
        "group": "android",
        "key": "android-arm32",
        "os": RUNNER_UBUNTU,
        "platform": "android",
        "arch": "arm32",
        "variant": "standard",
        "mono_flag": NO_MONO,
        "bin_suffix": "",
        "scons_extra": "",
        "artifact_glob": "android_libs/**",
        "timeout": 180,
    },
    {
        "group": "android",
        "key": "android-arm64",
        "os": RUNNER_UBUNTU,
        "platform": "android",
        "arch": "arm64",
        "variant": "standard",
        "mono_flag": NO_MONO,
        "bin_suffix": "",
        "scons_extra": "",
        "artifact_glob": "android_libs/**",
        "timeout": 180,
    },
    {
        "group": "android",
        "key": "android-x86_64",
        "os": RUNNER_UBUNTU,
        "platform": "android",
        "arch": "x86_64",
        "variant": "standard",
        "mono_flag": NO_MONO,
        "bin_suffix": "",
        "scons_extra": "",
        "artifact_glob": "android_libs/**",
        "timeout": 180,
    },
    {
        "group": "ios",
        "key": "ios",
        "os": RUNNER_MACOS,
        "platform": "ios",
        "target": "template_release",
        "variant": "standard",
        "mono_flag": NO_MONO,
        "bin_suffix": "",
        "scons_extra": "",
        "artifact_glob": "ios_out/**",
        "timeout": 300,
    },
    {
        "group": "macos",
        "key": "macos-release",
        "os": RUNNER_MACOS,
        "platform": "macos",
        "target": "template_release",
        "short_target": "release",
        "variant": "standard",
        "mono_flag": NO_MONO,
        "bin_suffix": "",
        "scons_extra": "",
        "artifact_glob": "macos_out/**",
        "timeout": 300,
    },
    {
        "group": "macos",
        "key": "macos-debug",
        "os": RUNNER_MACOS,
        "platform": "macos",
        "target": "template_debug",
        "short_target": "debug",
        "variant": "standard",
        "mono_flag": NO_MONO,
        "bin_suffix": "",
        "scons_extra": "",
        "artifact_glob": "macos_out/**",
        "timeout": 300,
    },
    # Mono/.NET builds (template-net-* artifacts, packaged into *_mono_export_templates.tpz).
    # Each entry additionally requires its base platform group to be selected.
    {
        "group": "dotnet",
        "requires": "windows",
        "key": "net-windows-release",
        "os": RUNNER_WINDOWS,
        "platform": "windows",
        "target": "template_release",
        "variant": "mono",
        "mono_flag": YES_MONO,
        "bin_suffix": ".mono",
        "scons_extra": "",
        "artifact_glob": "godot/bin/godot.windows.template_*.x86_64.mono*.exe",
        "timeout": 240,
    },
    {
        "group": "dotnet",
        "requires": "windows",
        "key": "net-windows-debug",
        "os": RUNNER_WINDOWS,
        "platform": "windows",
        "target": "template_debug",
        "variant": "mono",
        "mono_flag": YES_MONO,
        "bin_suffix": ".mono",
        "scons_extra": "",
        "artifact_glob": "godot/bin/godot.windows.template_*.x86_64.mono*.exe",
        "timeout": 240,
    },
    {
        "group": "dotnet",
        "requires": "linux",
        "key": "net-linux-release",
        "os": RUNNER_LINUX,
        "platform": "linux",
        "target": "template_release",
        "variant": "mono",
        "mono_flag": YES_MONO,
        "bin_suffix": ".mono",
        "scons_extra": "",
        "artifact_glob": "godot/bin/godot.linuxbsd.template_*.x86_64.mono",
        "timeout": 180,
    },
    {
        "group": "dotnet",
        "requires": "linux",
        "key": "net-linux-debug",
        "os": RUNNER_LINUX,
        "platform": "linux",
        "target": "template_debug",
        "variant": "mono",
        "mono_flag": YES_MONO,
        "bin_suffix": ".mono",
        "scons_extra": "",
        "artifact_glob": "godot/bin/godot.linuxbsd.template_*.x86_64.mono",
        "timeout": 180,
    },
    {
        "group": "dotnet",
        "requires": "android",
        "key": "net-android-arm32",
        "os": RUNNER_UBUNTU,
        "platform": "android",
        "arch": "arm32",
        "variant": "mono",
        "mono_flag": YES_MONO,
        "bin_suffix": "",
        "scons_extra": "",
        "artifact_glob": "android_libs/**",
        "timeout": 180,
    },
    {
        "group": "dotnet",
        "requires": "android",
        "key": "net-android-arm64",
        "os": RUNNER_UBUNTU,
        "platform": "android",
        "arch": "arm64",
        "variant": "mono",
        "mono_flag": YES_MONO,
        "bin_suffix": "",
        "scons_extra": "",
        "artifact_glob": "android_libs/**",
        "timeout": 180,
    },
    {
        "group": "dotnet",
        "requires": "android",
        "key": "net-android-x86_64",
        "os": RUNNER_UBUNTU,
        "platform": "android",
        "arch": "x86_64",
        "variant": "mono",
        "mono_flag": YES_MONO,
        "bin_suffix": "",
        "scons_extra": "",
        "artifact_glob": "android_libs/**",
        "timeout": 180,
    },
    {
        "group": "dotnet",
        "requires": "ios",
        "key": "net-ios",
        "os": RUNNER_MACOS,
        "platform": "ios",
        "target": "template_release",
        "variant": "mono",
        "mono_flag": YES_MONO,
        "bin_suffix": "",
        "scons_extra": "",
        "artifact_glob": "ios_out/**",
        "timeout": 300,
    },
    {
        "group": "dotnet",
        "requires": "macos",
        "key": "net-macos-release",
        "os": RUNNER_MACOS,
        "platform": "macos",
        "target": "template_release",
        "short_target": "release",
        "variant": "mono",
        "mono_flag": YES_MONO,
        "bin_suffix": ".mono",
        "scons_extra": "",
        "artifact_glob": "macos_out/**",
        "timeout": 300,
    },
    {
        "group": "dotnet",
        "requires": "macos",
        "key": "net-macos-debug",
        "os": RUNNER_MACOS,
        "platform": "macos",
        "target": "template_debug",
        "short_target": "debug",
        "variant": "mono",
        "mono_flag": YES_MONO,
        "bin_suffix": ".mono",
        "scons_extra": "",
        "artifact_glob": "macos_out/**",
        "timeout": 300,
    },
]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute the build matrix from selected platforms.")
    for group in GROUPS:
        parser.add_argument(f"--{group}", default="false", help=f"Enable the {group} platform jobs.")
    args = parser.parse_args()

    enabled = {group: getattr(args, group).strip().lower() in ("true", "1", "yes") for group in GROUPS}
    if not any(enabled.values()):
        fail("No platforms selected, nothing to build.")

    matrix = []
    for entry in ENTRIES:
        if not enabled[entry["group"]]:
            continue
        if entry["group"] == "dotnet" and not enabled[entry["requires"]]:
            continue
        matrix.append({key: value for key, value in entry.items() if key not in ("group", "requires")})

    if not matrix:
        if enabled["dotnet"]:
            fail(
                "The .NET/mono option requires at least one base platform to be selected "
                "(windows/linux/android/ios/macos)."
            )
        fail("No platforms selected, nothing to build.")

    payload = json.dumps({"include": matrix})
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            fh.write("matrix<<MATRIX_EOF\n")
            fh.write(payload + "\n")
            fh.write("MATRIX_EOF\n")
        keys = ", ".join(item["key"] for item in matrix)
        print(f"Matrix: {len(matrix)} job(s) enabled: {keys}", file=sys.stderr)
    else:
        print(payload)


if __name__ == "__main__":
    main()
