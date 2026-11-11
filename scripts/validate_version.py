#!/usr/bin/env python3
"""Validate the pinned Godot version in GODOT_VERSION against godotengine/godot.

Rules:
- The file must contain a single version line: "<major.minor[.patch]>-stable".
- Only stable releases are allowed: dev/beta/rc are rejected before any network call.
- The tag must exist as a published, non-prerelease release of godotengine/godot.
- Godot >= 4.1 is required (older versions lack SCons build_profile support).

Exit codes: 0 = valid, 1 = invalid, 2 = usage/environment error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

UPSTREAM_REPO = "godotengine/godot"
VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?-(stable)$")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def read_version(path: str) -> str:
    if not os.path.isfile(path):
        fail(f"Version file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        lines = [line.split("#", 1)[0].strip() for line in fh]
    lines = [line for line in lines if line]
    if not lines:
        fail(f"{path} is empty. Expected one line: <major.minor[.patch]>-stable")
    if len(lines) > 1:
        fail(f"{path} must contain exactly one version line, found {len(lines)}.")
    return lines[0]


def fetch_release(tag: str) -> dict | None:
    url = f"https://api.github.com/repos/{UPSTREAM_REPO}/releases/tags/{tag}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "godot-template-builder-validator",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        if err.code == 403:
            fail(
                "GitHub API request forbidden (most likely rate limiting). "
                "Retry later or set GITHUB_TOKEN to raise the limits."
            )
        fail(f"GitHub API error: HTTP {err.code} for tag '{tag}'.")
    except urllib.error.URLError as err:
        fail(f"Network error while contacting GitHub: {err.reason}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the pinned Godot version.")
    parser.add_argument("--file", default="GODOT_VERSION", help="Path to the version file.")
    parser.add_argument("--offline", action="store_true", help="Only check the file format (no network).")
    args = parser.parse_args()

    raw = read_version(args.file)
    match = VERSION_RE.match(raw)
    if not match:
        fail(
            f"'{raw}' is not a valid stable version.\n"
            "Expected format: <major.minor[.patch]>-stable (e.g. 4.7.2-stable).\n"
            "dev/beta/rc versions are not supported by this template."
        )
    major, minor = int(match.group(1)), int(match.group(2))
    tag = raw.removeprefix("v")
    if major < 4 or (major == 4 and minor < 1):
        fail(
            f"Godot {tag} is not supported: this template requires Godot >= 4.1 "
            "(SCons build_profile support)."
        )

    print(f"Version file: OK ('{tag}')")

    if args.offline:
        print("Offline mode: format checks passed, upstream lookup skipped.")
        return

    release = fetch_release(tag)
    if release is None:
        fail(
            f"Tag '{tag}' was not found in {UPSTREAM_REPO} releases.\n"
            f"Check https://github.com/{UPSTREAM_REPO}/releases and fix {args.file}."
        )
    if release.get("prerelease"):
        fail(f"'{tag}' is marked as a pre-release. Only stable releases are supported.")
    if release.get("draft"):
        fail(f"'{tag}' is a draft release.")
    print(f"Upstream check: OK (found {UPSTREAM_REPO} release '{release.get('name') or tag}')")

    outputs = {"tag": tag, "version": tag.removesuffix("-stable")}
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            for key, value in outputs.items():
                fh.write(f"{key}={value}\n")
        print(f"CI outputs written: {outputs}")


if __name__ == "__main__":
    main()
