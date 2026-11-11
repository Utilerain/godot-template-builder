#!/usr/bin/env python3
"""Assemble a Godot export templates .tpz package from CI build artifacts.

Layout matches the official export templates package:

  templates/<major.minor[.patch]>.<status>/
      windows_release_x86_64.exe
      windows_debug_x86_64.exe
      linux_release.x86_64
      linux_debug.x86_64
      version.txt

Linux binaries are stored with explicit Unix permission bits (0755), so this works
the same way on every CI runner regardless of the local filesystem.
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile

# (artifact dir, binary name inside the artifact, name inside the .tpz, executable)
FILES = [
    (
        "template-windows-template_release",
        "godot.windows.template_release.x86_64.exe",
        "windows_release_x86_64.exe",
        False,
    ),
    (
        "template-windows-template_debug",
        "godot.windows.template_debug.x86_64.exe",
        "windows_debug_x86_64.exe",
        False,
    ),
    (
        "template-linux-template_release",
        "godot.linuxbsd.template_release.x86_64",
        "linux_release.x86_64",
        True,
    ),
    (
        "template-linux-template_debug",
        "godot.linuxbsd.template_debug.x86_64",
        "linux_debug.x86_64",
        True,
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble the export templates .tpz package.")
    parser.add_argument("--tpl-dir", required=True, help="Template folder name, e.g. 4.7.2.stable")
    parser.add_argument("--tag", required=True, help="Godot tag, e.g. 4.7.2-stable")
    parser.add_argument("--artifacts", default="artifacts", help="Directory with downloaded CI artifacts")
    parser.add_argument("--output", default=".", help="Directory for the resulting .tpz")
    args = parser.parse_args()

    stage_root = os.path.join(".build", "stage")
    stage = os.path.join(stage_root, "templates", args.tpl_dir)
    os.makedirs(stage, exist_ok=True)
    executable_names = {dst for _dir, _src, dst, executable in FILES if executable}

    for artifact_dir, src_name, dst_name, executable in FILES:
        src = os.path.join(args.artifacts, artifact_dir, src_name)
        if not os.path.isfile(src):
            print(f"ERROR: missing artifact file: {src}", file=sys.stderr)
            sys.exit(1)
        dst = os.path.join(stage, dst_name)
        with open(src, "rb") as reader, open(dst, "wb") as writer:
            writer.write(reader.read())

    with open(os.path.join(stage, "version.txt"), "w", encoding="utf-8", newline="") as fh:
        fh.write(args.tpl_dir)

    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, f"Godot_v{args.tag}_export_templates.tpz")
    zip_root = stage_root
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for root, _dirs, files in os.walk(zip_root):
            for name in sorted(files):
                full = os.path.join(root, name)
                arcname = os.path.relpath(full, zip_root).replace(os.sep, "/")
                info = zipfile.ZipInfo.from_file(full, arcname)
                # Force Unix semantics so the permission bits below are meaningful
                # regardless of the OS this script runs on.
                info.create_system = 3
                info.external_attr = ((0o755 if executable_names & {name} else 0o644) << 16)
                with open(full, "rb") as fh:
                    archive.writestr(info, fh.read())

    size = os.path.getsize(out_path) / (1024 * 1024)
    print(f"Created {out_path} ({size:.1f} MiB)")
    with zipfile.ZipFile(out_path) as archive:
        for name in archive.namelist():
            info = archive.getinfo(name)
            perms = (info.external_attr >> 16) & 0o777
            print(f"  {name}  {info.file_size:>12,d} B  mode={oct(perms)}")


if __name__ == "__main__":
    main()
