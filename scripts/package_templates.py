#!/usr/bin/env python3
"""Assemble a Godot export templates .tpz package from CI build artifacts.

Layout matches the official export templates package:

  templates/<major.minor[.patch]>.<status>/
      windows_release_x86_64.exe           (+ _console.exe wrappers)
      windows_debug_x86_64.exe
      linux_release.x86_64
      linux_debug.x86_64
      web_[dlink_][nothreads_]release|debug.zip
      android_release.apk
      android_debug.apk
      android_source.zip
      ios.zip
      macos.zip
      version.txt

Only the platforms whose artifacts were downloaded are included; having no
usable artifacts at all is an error. Unix permission bits are written
explicitly (0755 for Linux executables), so the result is identical regardless
of the OS the packaging runs on.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import zipfile

EXEC = 0o755
NORM = 0o644

# (artifact dir, file inside the artifact, file inside the .tpz, permission mode)
# Artifact dirs are named "template-<matrix key>" by the build workflow.
FLAT_FILES = [
    # Windows (incl. console wrappers, as in the official templates)
    ("template-windows-release", "godot.windows.template_release.x86_64.exe", "windows_release_x86_64.exe", NORM),
    ("template-windows-release", "godot.windows.template_release.x86_64.console.exe", "windows_release_x86_64_console.exe", NORM),
    ("template-windows-debug", "godot.windows.template_debug.x86_64.exe", "windows_debug_x86_64.exe", NORM),
    ("template-windows-debug", "godot.windows.template_debug.x86_64.console.exe", "windows_debug_x86_64_console.exe", NORM),
    # Linux
    ("template-linux-release", "godot.linuxbsd.template_release.x86_64", "linux_release.x86_64", EXEC),
    ("template-linux-debug", "godot.linuxbsd.template_debug.x86_64", "linux_debug.x86_64", EXEC),
    # Web (all eight official wasm32 variants)
    ("template-web", "godot.web.template_release.wasm32.zip", "web_release.zip", NORM),
    ("template-web", "godot.web.template_release.wasm32.nothreads.zip", "web_nothreads_release.zip", NORM),
    ("template-web", "godot.web.template_release.wasm32.dlink.zip", "web_dlink_release.zip", NORM),
    ("template-web", "godot.web.template_release.wasm32.nothreads.dlink.zip", "web_dlink_nothreads_release.zip", NORM),
    ("template-web", "godot.web.template_debug.wasm32.zip", "web_debug.zip", NORM),
    ("template-web", "godot.web.template_debug.wasm32.nothreads.zip", "web_nothreads_debug.zip", NORM),
    ("template-web", "godot.web.template_debug.wasm32.dlink.zip", "web_dlink_debug.zip", NORM),
    ("template-web", "godot.web.template_debug.wasm32.nothreads.dlink.zip", "web_dlink_nothreads_debug.zip", NORM),
    # Android (produced by the gradle packaging job)
    ("template-android", "android_release.apk", "android_release.apk", NORM),
    ("template-android", "android_debug.apk", "android_debug.apk", NORM),
    ("template-android", "android_source.zip", "android_source.zip", NORM),
    # iOS (assembled by the iOS job)
    ("template-ios", "ios.zip", "ios.zip", NORM),
]

# macOS: assembled from the app-bundle template in the Godot sources + built executables.
MACOS_FILES = [
    ("template-macos-release", "godot_macos_release.arm64"),
    ("template-macos-release", "godot_macos_release.x86_64"),
    ("template-macos-debug", "godot_macos_debug.arm64"),
    ("template-macos-debug", "godot_macos_debug.x86_64"),
]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def stage_flat(stage: str, artifacts: str, included: list[str]) -> list[tuple[str, int]]:
    staged: list[tuple[str, int]] = []
    for artifact_dir, src_name, dst_name, mode in FLAT_FILES:
        if artifact_dir not in included:
            continue
        src = os.path.join(artifacts, artifact_dir, src_name)
        if not os.path.isfile(src):
            fail(f"missing artifact file: {src}")
        shutil.copyfile(src, os.path.join(stage, dst_name))
        staged.append((dst_name, mode))
    return staged


def assemble_macos(stage: str, artifacts: str, dist_dir: str | None, included: list[str]) -> list[tuple[str, int]]:
    present = [name for name, _src in MACOS_FILES if name in included]
    if not present:
        return []
    if not dist_dir or not os.path.isdir(os.path.join(dist_dir, "macos_template.app")):
        fail("macOS artifacts present but --dist-dir does not contain misc/dist/macos_template.app")

    build_root = os.path.join(stage, "macos_build")
    bundle = os.path.join(build_root, "macos_template.app")
    shutil.copytree(os.path.join(dist_dir, "macos_template.app"), bundle)
    macos_dir = os.path.join(bundle, "Contents", "MacOS")
    os.makedirs(macos_dir, exist_ok=True)

    for artifact_dir, src_name in MACOS_FILES:
        if artifact_dir not in included:
            continue
        src = os.path.join(artifacts, artifact_dir, src_name)
        if not os.path.isfile(src):
            fail(f"missing artifact file: {src}")
        dst = os.path.join(macos_dir, src_name)
        shutil.copyfile(src, dst)
        os.chmod(dst, EXEC)

    macos_zip = os.path.join(stage, "macos.zip")
    with zipfile.ZipFile(macos_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for root, _dirs, files in os.walk(build_root):
            for name in sorted(files):
                full = os.path.join(root, name)
                arcname = os.path.relpath(full, build_root).replace(os.sep, "/")
                mode = EXEC if "/Contents/MacOS/" in f"/{arcname}" else NORM
                info = zipfile.ZipInfo.from_file(full, arcname)
                info.create_system = 3
                info.external_attr = mode << 16
                with open(full, "rb") as fh:
                    archive.writestr(info, fh.read())
    shutil.rmtree(build_root)
    return [("macos.zip", NORM)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble the export templates .tpz package.")
    parser.add_argument("--tpl-dir", required=True, help="Template folder name, e.g. 4.7.2.stable")
    parser.add_argument("--tag", required=True, help="Godot tag, e.g. 4.7.2-stable")
    parser.add_argument("--artifacts", default="artifacts", help="Directory with downloaded CI artifacts")
    parser.add_argument("--dist-dir", default=None, help="Path to godot misc/dist (needed when macOS is built)")
    parser.add_argument("--output", default=".", help="Directory for the resulting .tpz")
    args = parser.parse_args()

    if not os.path.isdir(args.artifacts):
        fail(f"artifacts directory not found: {args.artifacts}")
    included = sorted(
        name
        for name in os.listdir(args.artifacts)
        if name.startswith("template-") and os.path.isdir(os.path.join(args.artifacts, name))
    )
    if not included:
        fail("no platform artifacts were downloaded; nothing to package")

    stage = os.path.join(".build", "stage", "templates", args.tpl_dir)
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage, exist_ok=True)

    staged = stage_flat(stage, args.artifacts, included)
    staged += assemble_macos(stage, args.artifacts, args.dist_dir, included)
    if not staged:
        fail(
            "none of the downloaded artifacts map to template files.\n"
            f"Artifact dirs seen: {', '.join(included)}\n"
            "Expected dirs like: template-windows-release, template-linux-release, "
            "template-web, template-android, template-ios, template-macos-release, ..."
        )

    with open(os.path.join(stage, "version.txt"), "w", encoding="utf-8", newline="") as fh:
        fh.write(args.tpl_dir)

    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, f"Godot_v{args.tag}_export_templates.tpz")
    zip_root = os.path.join(".build", "stage")
    exec_names = {dst for dst, mode in staged if mode == EXEC}
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for root, _dirs, files in os.walk(zip_root):
            for name in sorted(files):
                full = os.path.join(root, name)
                arcname = os.path.relpath(full, zip_root).replace(os.sep, "/")
                info = zipfile.ZipInfo.from_file(full, arcname)
                info.create_system = 3
                mode = EXEC if arcname.endswith(tuple(exec_names)) else NORM
                info.external_attr = mode << 16
                with open(full, "rb") as fh:
                    archive.writestr(info, fh.read())

    size = os.path.getsize(out_path) / (1024 * 1024)
    print(f"Created {out_path} ({size:.1f} MiB) with {len(staged)} template file(s):")
    for name, _mode in sorted(staged):
        print(f"  templates/{args.tpl_dir}/{name}")


if __name__ == "__main__":
    main()
