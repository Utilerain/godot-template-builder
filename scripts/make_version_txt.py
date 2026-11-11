#!/usr/bin/env python3
"""Compute the export templates folder name from the checked-out Godot sources.

Reads core/version.py (the source of truth for version numbers) and prints:

  template_dir=<major.minor[.patch]>.<status>
  version_txt=<same string>

The editor looks for templates in
`export_templates/<GODOT_VERSION_FULL_CONFIG>/...` where the folder name is
"major.minor.patch.status" with the patch omitted when it is 0
(see core/version.h: GODOT_VERSION_FULL_CONFIG).

Human-readable info goes to stderr, machine-readable lines to stdout,
so the script can be used with GITHUB_OUTPUT directly.
"""

from __future__ import annotations

import argparse
import re
import sys

ASSIGN_RE = re.compile(r"^(\w+)\s*=\s*(.+?)\s*$")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def parse_version_file(path: str) -> dict:
    fields: dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError as err:
        fail(f"Cannot read {path}: {err}")
    for line in content.splitlines():
        match = ASSIGN_RE.match(line)
        if not match:
            continue
        name, value = match.group(1), match.group(2)
        if name in {"major", "minor", "patch", "status"}:
            fields[name] = value.strip().strip("'\"")
    missing = {"major", "minor", "status"} - set(fields)
    if missing:
        fail(f"{path} is missing expected fields: {sorted(missing)}")
    return fields


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute export templates folder name from Godot sources.")
    parser.add_argument("--version-file", default="godot/core/version.py")
    args = parser.parse_args()

    fields = parse_version_file(args.version_file)
    major, minor, status = fields["major"], fields["minor"], fields["status"]
    patch = fields.get("patch", "0")
    try:
        patch_num = int(patch)
    except ValueError:
        fail(f"Unexpected patch value in {args.version_file}: '{patch}'")

    if status != "stable":
        fail(f"Refusing to package non-stable status '{status}': only stable builds are supported.")

    template_dir = f"{major}.{minor}" + (f".{patch_num}" if patch_num else "") + f".{status}"
    print(f"template_dir={template_dir}")
    print(f"version_txt={template_dir}")
    print(f"Godot {template_dir} parsed from {args.version_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
