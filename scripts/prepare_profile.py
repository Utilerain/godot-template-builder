#!/usr/bin/env python3
"""Check the Godot build profile used for custom export template builds.

The profile is normally created inside the Godot editor via
Project > Tools > Engine Compilation Configuration Editor (a ".gdbuild" JSON file).

This script:
- validates the file structure before hours-long CI builds are started;
- prints a human-readable summary of what will be disabled;
- always writes a normalized profile file so the build step can pass it to SCons.

If no profile exists, an empty (no-op) profile is written so builds still work.

Exit codes: 0 = OK, 1 = invalid profile.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

EMPTY_PROFILE = {"disabled_build_options": {}, "disabled_classes": []}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


def resolve_input(path: str) -> str | None:
    if os.path.isfile(path):
        return path
    if path.endswith(".json"):
        sibling = path[:-5] + ".gdbuild"
        if os.path.isfile(sibling):
            warn(f"'{path}' not found, using sibling '{sibling}' instead.")
            return sibling
    return None


def preview(values, limit: int = 20) -> str:
    shown = sorted(str(value) for value in values)[:limit]
    more = len(list(values)) - len(shown)
    result = ", ".join(f"`{value}`" for value in shown)
    if more > 0:
        result += f", ... (+{more} more)"
    return result or "-"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the build profile for export template builds.")
    parser.add_argument("--input", default="profiles/build_profile.json")
    parser.add_argument("--output", default=".build/profile.gdbuild")
    args = parser.parse_args()

    source = resolve_input(args.input)
    if source is None:
        warn("No build profile found - the templates will be built with the standard feature set.")
        warn("Create one in the Godot editor: Project > Tools > Engine Compilation Configuration Editor,")
        warn("then save it as profiles/build_profile.json and commit it.")
        data = dict(EMPTY_PROFILE)
    else:
        with open(source, "r", encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as err:
                fail(f"Profile '{source}' is not valid JSON: {err}")
        if not isinstance(data, dict):
            fail(f"Profile '{source}' must be a JSON object.")
        if data.get("type") == "feature_profile" or (
            "classes" in data and "disabled_classes" not in data
        ):
            fail(
                f"'{source}' looks like an EDITOR feature profile, not a build profile.\n"
                "Feature profiles only hide classes in the editor UI and cannot be used to compile templates.\n"
                "Use Project > Tools > Engine Compilation Configuration Editor instead and save the .gdbuild file here."
            )
        allowed = {"type", "disabled_build_options", "disabled_classes"}
        unknown = set(data) - allowed
        if unknown:
            fail(f"Profile '{source}' has unsupported keys: {sorted(unknown)}. Expected: {sorted(allowed)}.")

    options = data.get("disabled_build_options", {})
    classes = data.get("disabled_classes", [])
    if not isinstance(options, dict) or not all(isinstance(key, str) for key in options):
        fail("'disabled_build_options' must be an object of {scons_option: value}.")
    if not isinstance(classes, list) or not all(isinstance(item, str) for item in classes):
        fail("'disabled_classes' must be an array of class names.")
    if "type" in data and data["type"] != "build_profile":
        fail(f"Unexpected profile type '{data['type']}', expected 'build_profile'.")

    normalized = {"disabled_build_options": options, "disabled_classes": classes}

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(normalized, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"Profile: {source or '(none)'}")
    print(f"  disabled build options ({len(options)}): {preview(options.keys())}")
    print(f"  disabled classes ({len(classes)}): {preview(classes)}")
    print(f"Normalized profile written to: {args.output}")


if __name__ == "__main__":
    main()
