#!/usr/bin/env python3
"""Generate GitHub release notes for the custom export templates package."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile


def build_profile_section(profile_path: str) -> str:
    try:
        with open(profile_path, "r", encoding="utf-8") as fh:
            profile = json.load(fh)
    except FileNotFoundError:
        return "No build profile was committed - the templates contain the standard feature set."

    options = profile.get("disabled_build_options", {})
    classes = profile.get("disabled_classes", [])
    if not options and not classes:
        return "The committed build profile is empty - the templates contain the standard feature set."

    lines = []
    if options:
        opts = ", ".join(f"`{key}`" for key in sorted(options))
        lines.append(f"- Disabled build options ({len(options)}): {opts}")
    if classes:
        limit = 60
        shown = ", ".join(f"`{name}`" for name in sorted(classes)[:limit])
        if len(classes) > limit:
            shown += f", ... (+{len(classes) - limit} more)"
        lines.append(f"- Disabled classes ({len(classes)}): {shown}")

    return (
        "Templates are compiled with the build profile committed in this repository:\n\n"
        + "\n".join(lines)
    )


def list_tpz_contents(tpz_path: str, tpl_dir: str) -> list[tuple[str, int]]:
    prefix = f"templates/{tpl_dir}/"
    entries = []
    with zipfile.ZipFile(tpz_path) as archive:
        for name in archive.namelist():
            if name.startswith(prefix) and name != f"{prefix}version.txt":
                entries.append((name[len(prefix):], archive.getinfo(name).file_size))
    return sorted(entries)


def format_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MiB"
    return f"{size / 1024:.0f} KiB"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate release notes markdown.")
    parser.add_argument("--tag", required=True, help="Godot tag, e.g. 4.7.2-stable")
    parser.add_argument("--tpl-dir", required=True, help="Template folder name, e.g. 4.7.2.stable")
    parser.add_argument("--tpz", required=True, help="Path to the assembled .tpz package")
    parser.add_argument("--profile", default=".build/profile.gdbuild")
    parser.add_argument("--repo-sha", default="", help="Commit SHA of this repository used for the build")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    entries = list_tpz_contents(args.tpz, args.tpl_dir)
    contents_table = "\n".join(
        f"| `{name}` | {format_size(size)} |" for name, size in entries
    )

    sha = f" (repo commit `{args.repo_sha[:12]}`)" if args.repo_sha else ""
    text = f"""## Custom export templates for Godot {args.tag}

Built by **godot-template-builder** from the official [godotengine/godot `{args.tag}` sources](https://github.com/godotengine/godot/releases/tag/{args.tag}){sha}.

> Only **stable** Godot releases are ever built here - `dev`/`beta`/`rc` versions are rejected by the validator.

### Package contents - `Godot_v{args.tag}_export_templates.tpz` (folder `templates/{args.tpl_dir}/`)

| File | Size |
| --- | --- |
{contents_table}

Covered by this build: **Windows & Linux (x86_64, incl. console wrappers)**, **Web** (all 8 official wasm32 variants incl. dlink/nothreads), **Android** (arm32/arm64/x86_64 APKs + source), **iOS** (arm64 device + x86_64 simulator static libs, Xcode project and xcframeworks in `ios.zip`), **macOS** (x86_64 + arm64 inside `macos.zip`/`macos_template.app`).

### Build profile

{build_profile_section(args.profile)}

### Notes & limitations

- x86_64 only for Windows/Linux; the `mono`/.NET module is disabled everywhere; no editor binaries are included.
- Android x86_32 (legacy 32-bit) is not built.
- Classes disabled by the build profile are removed at compile time - exporting a project that uses them will fail at runtime.
- The editor picks this package up automatically because the version matches `{args.tag}`; if you ever see a version-mismatch warning, the templates were built from a different Godot release.

### Install

- **Windows:** unzip so that `%APPDATA%\\Godot\\export_templates\\{args.tpl_dir}\\` contains the files above.
- **Linux:** unzip so that `~/.local/share/godot/export_templates/{args.tpl_dir}/` contains the files above.
- The other platform files live in the same folder and are picked up automatically.
"""
    with open(args.output, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"Release notes written to {args.output} ({len(entries)} template files listed)", file=sys.stderr)


if __name__ == "__main__":
    main()
