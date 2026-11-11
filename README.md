# godot-template-builder

A repository template that automatically builds **custom Godot export templates** for **Windows & Linux (x86_64)** — aimed at UI-style applications. You decide what gets stripped out of the engine via a build profile created inside the Godot editor; the CI does the rest.

## How it works

```
GODOT_VERSION ────► validate: stable-only check against godotengine/godot
profiles/*.json ──► build profile (optional, made in the Godot editor)
                        │
                        ▼
          GitHub Actions: scons × 4 jobs
          (linux / windows × template_release / template_debug)
                        │
                        ▼
          Godot_v<version>_export_templates.tpz
                        │
                        ▼
          GitHub Release (tag: godot-<version>)
```

- The engine version is pinned in [`GODOT_VERSION`](GODOT_VERSION).
- **Only stable releases are ever built.** `dev`/`beta`/`rc` are rejected by the validator and the build never starts. This is a hard rule of this template.
- The build profile is created by you in the Godot editor (see below) and committed to `profiles/`.

## Quick start

1. Use this repo as a template (or copy it), then pick a stable Godot release in `GODOT_VERSION` (e.g. `4.7.2-stable`). The validator checks it against the real [godotengine/godot releases](https://github.com/godotengine/godot/releases).
2. Create a build profile in the Godot editor: **Project → Tools → Engine Compilation Configuration Editor** (available since Godot 4.5). Disable what your UI apps don't need, **Save As** into `profiles/build_profile.json`, and commit. See [profiles/README.md](profiles/README.md) for details.
   *(No profile committed? CI builds with the standard feature set and warns you.)*
3. Go to **Actions → Build export templates → Run workflow**. Optionally add extra SCons args (e.g. `vulkan=no` to also strip the Vulkan/RenderingDevice renderer).
4. When the run finishes (~1.5–2.5 h), grab the `.tpz` from **Releases** and unzip it into the Godot user data dir (paths below).

## GODOT_VERSION

A single line, format `<major.minor[.patch]>-stable`:

```
4.7.2-stable
```

- `dev`/`beta`/`rc` suffixes → rejected (offline check, nothing is built).
- The tag must exist as a published stable release of `godotengine/godot` (GitHub API check).
- Godot ≥ 4.1 is required (SCons `build_profile` support). The in-editor profile editor itself requires ≥ 4.5.

Validate locally:

```sh
python scripts/validate_version.py --file GODOT_VERSION
```

## Creating the build profile in Godot

1. Open any project in Godot (the profile is created per project).
2. **Project → Tools → Engine Compilation Configuration Editor**.
3. Uncheck what you don't need. For a UI-only template that is typically: 3D classes (`Node3D` and descendants), physics, navigation, XR; audio if not needed. Start with **Detect from Project** — it auto-disables everything the project doesn't use — then review manually.
4. **Save As** → `profiles/build_profile.json`, commit it.

Details and the file format reference: [profiles/README.md](profiles/README.md).

## Running the build

**Actions → Build export templates → Run workflow.** The pipeline:

| Job | What it does |
| --- | --- |
| `validate` | checks `GODOT_VERSION` against upstream releases + checks the profile |
| `build` (×4) | `scons platform=… target=template_release\|template_debug arch=x86_64 module_mono_enabled=no build_profile=…` |
| `package-release` | assembles the `.tpz` (same layout as the official one) and publishes a GitHub release tagged `godot-<version>` |

Each re-run for the same version updates the existing release instead of creating duplicates.

## Installing the templates

Unzip the `.tpz` so that the template folder sits directly under the Godot `export_templates` dir:

- **Windows:** `%APPDATA%\Godot\export_templates\`
- **Linux:** `~/.local/share/godot/export_templates/`

Example layout:

```
%APPDATA%\Godot\export_templates\4.7.2.stable\windows_release_x86_64.exe
```

The editor picks templates up automatically when the folder version matches the editor's own version — that is exactly why only stable releases are built here.

## Limitations & notes

- x86_64 only (Windows + Linux). Other platforms/arches → extend the matrix in `.github/workflows/build.yml`.
- Built with `module_mono_enabled=no`: .NET/C# projects will not run with these templates.
- No editor binary is built — export templates only.
- Classes disabled in the build profile are removed at compile time; exporting a project that uses them fails at runtime. Test before you build.
- Templates are built from the official Godot sources at the pinned tag plus the committed profile — nothing else is patched.

## Repository layout

```
GODOT_VERSION            ← pinned engine version (stable only)
profiles/                ← your build profile (build_profile.json) + how-to
scripts/                 ← validator, profile check, packaging, release notes
.github/workflows/
  build.yml              ← validate → build ×4 → package → release
  validate.yml           ← quick validation on push/PR
```

## FAQ

**Why stable only?**
Export templates must match the editor's exact version — the editor looks them up by its own version string. Pinning stable releases keeps everything reproducible and lets the editor find the templates without overrides.

**Can I build beta/rc?**
Not with this template, by design: the validator and the packaging step both refuse non-stable versions.

**How do I make the binaries even smaller?**
Pass extra SCons args in the workflow dispatch, e.g. `vulkan=no` (drops the RenderingDevice/Vulkan renderer; exported projects must then use the `gl_compatibility` rendering method). See also the official [size optimization guide](https://docs.godotengine.org/en/stable/engine_details/development/compiling/optimizing_for_size.html) and the [Engine Compilation Configuration Editor docs](https://docs.godotengine.org/en/stable/tutorials/editor/using_engine_compilation_configuration_editor.html).

**Does re-running the build cost anything special?**
SCons build caches are stored per platform/target/version, so re-runs are usually faster than the first build.
