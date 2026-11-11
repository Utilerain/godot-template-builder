#!/usr/bin/env python3
"""Build the dynamic build matrix for the build workflow from the selected platforms.

Each platform group maps to a workflow_dispatch boolean input. The output is a
JSON matrix ({"include": [...]}) written to GITHUB_OUTPUT for consumption via
fromJson().
"""

from __future__ import annotations

import argparse
import json
import os
import sys

GROUPS = ("windows", "linux", "web", "android", "ios", "macos")

ENTRIES = [
    {
        "group": "windows",
        "key": "windows-release",
        "os": "windows-latest",
        "platform": "windows",
        "target": "template_release",
        "scons_extra": "debug_symbols=no",
        "artifact_glob": "godot/bin/godot.windows.template_release.x86_64*.exe",
        "timeout": 240,
    },
    {
        "group": "windows",
        "key": "windows-debug",
        "os": "windows-latest",
        "platform": "windows",
        "target": "template_debug",
        "scons_extra": "debug_symbols=yes",
        "artifact_glob": "godot/bin/godot.windows.template_debug.x86_64*.exe",
        "timeout": 240,
    },
    {
        "group": "linux",
        "key": "linux-release",
        "os": "ubuntu-latest",
        "platform": "linux",
        "target": "template_release",
        "scons_extra": "use_static_cpp=yes debug_symbols=no",
        "artifact_glob": "godot/bin/godot.linuxbsd.template_release.x86_64",
        "timeout": 180,
    },
    {
        "group": "linux",
        "key": "linux-debug",
        "os": "ubuntu-latest",
        "platform": "linux",
        "target": "template_debug",
        "scons_extra": "use_static_cpp=yes",
        "artifact_glob": "godot/bin/godot.linuxbsd.template_debug.x86_64",
        "timeout": 180,
    },
    {
        "group": "web",
        "key": "web",
        "os": "ubuntu-latest",
        "platform": "web",
        "target": "template_release",
        "scons_extra": "",
        "artifact_glob": "godot/bin/godot.web.template_*.wasm32*.zip",
        "timeout": 300,
    },
    {
        "group": "android",
        "key": "android-arm32",
        "os": "ubuntu-latest",
        "platform": "android",
        "arch": "arm32",
        "scons_extra": "",
        "artifact_glob": "android_libs/**",
        "timeout": 180,
    },
    {
        "group": "android",
        "key": "android-arm64",
        "os": "ubuntu-latest",
        "platform": "android",
        "arch": "arm64",
        "scons_extra": "",
        "artifact_glob": "android_libs/**",
        "timeout": 180,
    },
    {
        "group": "android",
        "key": "android-x86_64",
        "os": "ubuntu-latest",
        "platform": "android",
        "arch": "x86_64",
        "scons_extra": "",
        "artifact_glob": "android_libs/**",
        "timeout": 180,
    },
    {
        "group": "ios",
        "key": "ios",
        "os": "macos-26",
        "platform": "ios",
        "target": "template_release",
        "scons_extra": "",
        "artifact_glob": "ios_out/**",
        "timeout": 300,
    },
    {
        "group": "macos",
        "key": "macos-release",
        "os": "macos-26",
        "platform": "macos",
        "target": "template_release",
        "scons_extra": "debug_symbols=no",
        "artifact_glob": "macos_out/**",
        "timeout": 300,
    },
    {
        "group": "macos",
        "key": "macos-debug",
        "os": "macos-26",
        "platform": "macos",
        "target": "template_debug",
        "scons_extra": "debug_symbols=yes",
        "artifact_glob": "macos_out/**",
        "timeout": 300,
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute the build matrix from selected platforms.")
    for group in GROUPS:
        parser.add_argument(f"--{group}", default="false", help=f"Enable the {group} platform jobs.")
    args = parser.parse_args()

    enabled = {group: getattr(args, group).strip().lower() in ("true", "1", "yes") for group in GROUPS}
    if not any(enabled.values()):
        print("ERROR: no platforms selected, nothing to build.", file=sys.stderr)
        sys.exit(1)

    matrix = [
        {key: value for key, value in entry.items() if key != "group"}
        for entry in ENTRIES
        if enabled[entry["group"]]
    ]

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
