#!/usr/bin/env python3
"""Generate GitHub release notes for the custom export templates package(s)."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


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


def list_tpz_contents(tpz_path: str) -> tuple[str, list[tuple[str, int]]]:
    """List template files inside the .tpz as ((template folder), [(file name, size), ...])."""
    entries = []
    folder = ""
    with zipfile.ZipFile(tpz_path) as archive:
        for name in archive.namelist():
            parts = name.split("/")
            # templates/<folder>/<file> — top-level template files only
            if len(parts) == 3 and parts[0] == "templates" and parts[2] != "version.txt":
                folder = parts[1]
                entries.append((name[len(f"templates/{folder}/"):], archive.getinfo(name).file_size))
    return folder, sorted(entries)


def format_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MiB"
    return f"{size / 1024:.0f} KiB"


def package_section(tpz_path: str, tpl_dir: str) -> str:
    folder, entries = list_tpz_contents(tpz_path)
    if not entries or not folder:
        fail(f"{tpz_path}: no template files found inside the archive (expected templates/<folder>/<file> entries)")
    if tpl_dir and folder not in (tpl_dir, f"{tpl_dir}.mono"):
        fail(
            f"{tpz_path}: template folder inside the archive is '{folder}', "
            f"expected '{tpl_dir}' (standard) or '{tpl_dir}.mono' (mono)"
        )
    rows = "\n".join(f"| `{name}` | {format_size(size)} |" for name, size in entries)
    return f"\n#### `{tpz_path}` (folder `{folder}`)\n\n| File | Size |\n| --- | --- |\n{rows}\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate release notes markdown.")
    parser.add_argument("--tag", required=True, help="Godot tag, e.g. 4.7.2-stable")
    parser.add_argument("--tpz", required=True, action="append", help="Path to an assembled .tpz (repeatable)")
    parser.add_argument("--tpl-dir", default="", help="Expected template folder name, e.g. 4.7.2.stable (cross-checked against each archive)")
    parser.add_argument("--profile", default=".build/profile.gdbuild")
    parser.add_argument("--repo-sha", default="", help="Commit SHA of this repository used for the build")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    packages = "\n".join(package_section(path, args.tpl_dir) for path in args.tpz)
    mono_note = ""
    if len(args.tpz) > 1:
        mono_note = (
            "\nThe `*_mono_export_templates.tpz` package is the same idea with the C#/.NET runtime "
            "compiled in; it installs into `export_templates/<version>.mono/` and must only be used "
            "with the .NET-enabled Godot editor. It does not include Web templates (.NET is not "
            "supported on Web)."
        )

    sha = f" (repo commit `{args.repo_sha[:12]}`)" if args.repo_sha else ""
    text = f"""## Custom export templates for Godot {args.tag}

Built by **godot-template-builder** from the official [godotengine/godot `{args.tag}` sources](https://github.com/godotengine/godot/releases/tag/{args.tag}){sha}.

> Only **stable** Godot releases are ever built here - `dev`/`beta`/`rc` versions are rejected by the validator.

### Package contents{packages}
{mono_note}
Coverage of this build: **Windows & Linux (x86_64, incl. console wrappers)**, **Web** (all 8 official wasm32 variants incl. dlink/nothreads; standard package only), **Android** (arm32/arm64/x86_64 APKs + source), **iOS** (arm64 device + x86_64 simulator static libs, Xcode project and xcframeworks in `ios.zip`), **macOS** (universal x86_64+arm64 inside `macos.zip`/`macos_template.app`).

### Build profile

{build_profile_section(args.profile)}

### Notes & limitations

- x86_64 only for Windows/Linux; no editor binaries are included.
- Android x86_32 (legacy 32-bit) is not built.
- Classes disabled by the build profile are removed at compile time - exporting a project that uses them will fail at runtime.
- The editor picks this package up automatically because the version matches `{args.tag}`; if you ever see a version-mismatch warning, the templates were built from a different Godot release.
- The macOS templates are not codesigned - sign at export time with your own identity.

### Install

- **Windows:** unzip so that `%APPDATA%\\Godot\\export_templates\\` contains the `templates` folder contents.
- **Linux:** unzip so that `~/.local/share/godot/export_templates/` contains the `templates` folder contents.
- Installing through the editor (**Editor → Manage Export Templates → Install from File**) also works: the editor extracts everything into its own versioned folder automatically.
"""
    with open(args.output, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"Release notes written to {args.output} ({len(args.tpz)} package(s) listed)", file=sys.stderr)


if __name__ == "__main__":
    main()
