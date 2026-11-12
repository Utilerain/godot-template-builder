# godot-template-builder

A repository template that automatically builds **custom Godot export templates**. You decide what gets stripped out of the engine via a build profile created inside the Godot editor; the CI does the rest.

Supported platforms: **Windows**, **Linux** (x86_64), **Web** (wasm32), **Android** (arm32/arm64/x86_64), **iOS** (arm64 device + x86_64 simulator), **macOS** (universal x86_64+arm64) — plus an optional **.NET/mono** variant (a separate `*_mono_export_templates.tpz` package; not available for Web). Windows and Linux are built by default; the rest are opt-in per run.

## How it works

```
GODOT_VERSION ────► validate: stable-only check against godotengine/godot
profiles/*.json ──► build profile (optional, made in the Godot editor)
platform picklist ─► dynamic build matrix:
                      win/linux x86_64, web (8 variants), android (3 archs + gradle),
                      ios (device+simulator), macos (universal x86_64+arm64)
                      optional .NET/mono variants → *_mono_export_templates.tpz
                        │
                        ▼
          Godot_v<version>_export_templates.tpz  (official layout)
                        │
                        ▼
          GitHub Release (tag: godot-<version>)
```

- The engine version is pinned in [`GODOT_VERSION`](GODOT_VERSION).
- **Only stable releases are ever built.** `dev`/`beta`/`rc` are rejected by the validator and the build never starts. This is a hard rule of this template.
- The build profile is created by you in the Godot editor (see below) and committed to `profiles/`.

## Quick start

1. Use this repo as a template (or copy it), then pick a stable Godot release in `GODOT_VERSION` (e.g. `4.7.2-stable`). The validator checks it against the real [godotengine/godot releases](https://github.com/godotengine/godot/releases).
2. Create a build profile in the Godot editor: **Project → Tools → Engine Compilation Configuration Editor** (available since Godot 4.5). Disable what your app or game don't need, **Save As** into `profiles/build_profile.json`, and commit. See [profiles/README.md](profiles/README.md) for details.
   *(No profile committed? CI builds with the standard feature set and warns you.)*
3. Go to **Actions → Build export templates → Run workflow** and tick the platforms you need. Optionally add extra SCons args (e.g. `vulkan=no` to strip the Vulkan/RenderingDevice renderer).
4. When the run finishes, grab the `.tpz` from **Releases** and unzip it into the Godot user data dir (paths below).

### ⚠️ GitHub Actions minutes (private repos)

Hosted runners are billed with multipliers: **Linux 1×, Windows 2×, macOS 10×**. On the free plan (~2,000 min/month) a full run with everything enabled will not fit. Rough per-run cost of this pipeline:

| Platform | Jobs | Approx. wall time | Multiplier |
| --- | --- | --- | --- |
| Windows x86_64 | 2 | ~1.5–2.5 h | 2× |
| Linux x86_64 | 2 | ~40–60 min | 1× |
| Web (8 variants) | 1 | ~1.5–2 h | 1× |
| Android (3 archs + gradle) | 4 | ~40–80 min | 1× |
| iOS | 1 | ~1.5–2.5 h | **10×** |
| macOS | 2 | ~1.5–2.5 h | **10×** |
| .NET/mono add-on | +1 glue job, +1 job per selected platform | +40–80 min per platform | follows the platform |

Windows/Linux are on by default; enable the rest only when you actually need them.

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
3. Uncheck what you don't need — for example 3D classes (`Node3D` and descendants), physics, navigation, XR or audio, if your projects never use them. Start with **Detect from Project** — it auto-disables everything the project doesn't use — then review manually.
4. **Save As** → `profiles/build_profile.json`, commit it.

Details and the file format reference: [profiles/README.md](profiles/README.md).

## Running the build

**Actions → Build export templates → Run workflow.** The pipeline:

| Job | What it does |
| --- | --- |
| `validate` | checks `GODOT_VERSION` against upstream releases, checks the profile, computes the matrix from the picked platforms |
| `net-glue` | (only with .NET) builds a Linux mono editor and generates the mono glue for all mono builds |
| `build` (matrix) | one job per platform/target/variant; each runs the platform-appropriate toolchain (scons, emscripten, NDK, Xcode) |
| `android-gradle` / `net-android-gradle` | packs the Android native libraries into `android_release.apk` / `android_debug.apk` / `android_source.zip` (standard and mono variants) |
| `package-release` | assembles the `.tpz` package(s) (same layout as the official ones) and publishes a GitHub release tagged `godot-<version>` |

Each re-run for the same version updates the existing release instead of creating duplicates.

### Platform notes

- **Web**: all 8 official wasm32 variants (`web_[dlink_][nothreads_]release|debug.zip`), built with the Emscripten version pinned by Godot's own CI for that release (4.0.11 for 4.7.2).
- **Android**: `arm32`, `arm64`, `x86_64` (legacy `x86_32` is skipped). Java 17 + NDK 29.0.14206865 + SDK 36 are provisioned automatically; the APKs are packed by Godot's own gradle task.
- **iOS**: arm64 device + x86_64 simulator static libraries; `ios.zip` also embeds the Xcode project template and `MoltenVK.xcframework` (from the LunarG Vulkan SDK), matching the official package.
- **macOS**: universal (lipo-merged x86_64+arm64) executables inside `macos_template.app` (`macos.zip`); ANGLE/AccessKit/MoltenVK are installed from Godot's own `misc/scripts/install_*.py|.sh` installers and degrade gracefully if unavailable.
- **.NET/mono**: a separate `*_mono_export_templates.tpz` that installs into `export_templates/<version>.mono/` and pairs only with the .NET-enabled Godot editor. Built from the same sources plus the mono glue generated by a one-off Linux editor build (the standard package ships `icudt_godot.dat` too, as the official ones do). Web has no .NET support, matching upstream.
- The macOS templates are **not codesigned** (the official ones aren't either) — sign at export time with your own identity.

## Installing the templates

Unzip the `.tpz` so that the template folder sits directly under the Godot `export_templates` dir:

- **Windows:** `%APPDATA%\Godot\export_templates\`
- **Linux:** `~/.local/share/godot/export_templates/`

Example layout:

```
%APPDATA%\Godot\export_templates\4.7.2.stable\windows_release_x86_64.exe
```

The editor picks templates up automatically when the folder version matches the editor's own version — that is exactly why only stable releases are built here. The web/android/ios/macos files live in the same folder and are picked up automatically too. The mono package installs into the sibling `<version>.mono` folder and pairs with the .NET-enabled editor; installing via **Editor → Manage Export Templates → Install from File** works for both packages.

## Limitations & notes

- x86_64 only for Windows/Linux; no editor binaries are built (except the one-off Linux editor used to generate the mono glue for .NET packages).
- The .NET/mono variant does not include Web templates — upstream does not support .NET on Web.
- Android x86_32 (legacy 32-bit) is not built.
- Classes disabled in the build profile are removed at compile time; exporting a project that uses them fails at runtime. Test before you build.
- Templates are built from the official Godot sources at the pinned tag plus the committed profile — nothing else is patched.

## Repository layout

```
GODOT_VERSION              ← pinned engine version (stable only)
profiles/                  ← your build profile (build_profile.json) + how-to
scripts/
  validate_version.py      ← stable-only version validator (GitHub API)
  prepare_profile.py       ← build profile validation/summary
  make_matrix.py           ← dynamic platform matrix for the workflow
  build_web.sh             ← all 8 web variants (parallel waves)
  package_ios.sh           ← ios.zip assembly (official layout)
  package_templates.py     ← .tpz assembly from CI artifacts
  make_version_txt.py      ← template folder name from the engine sources
  make_release_notes.py    ← release notes from the assembled .tpz
.github/workflows/
  build.yml                ← validate → net-glue → build matrix → android-gradle → package → release
  validate.yml             ← quick validation on push/PR
```

## FAQ

**Why stable only?**
Export templates must match the editor's exact version — the editor looks them up by its own version string. Pinning stable releases keeps everything reproducible and lets the editor find the templates without overrides.

**Can I build beta/rc?**
Not with this template, by design: the validator and the packaging step both refuse non-stable versions.

**How do I make the binaries even smaller?**
Pass extra SCons args in the workflow dispatch, e.g. `vulkan=no` (drops the RenderingDevice/Vulkan renderer where applicable; exported projects must then use the `gl_compatibility` rendering method). See also the official [size optimization guide](https://docs.godotengine.org/en/stable/engine_details/development/compiling/optimizing_for_size.html) and the [Engine Compilation Configuration Editor docs](https://docs.godotengine.org/en/stable/tutorials/editor/using_engine_compilation_configuration_editor.html).

**Can I add other platforms (arm64 Windows/Linux, x86_32 Android)?**
The pipeline structure is in `.github/workflows/build.yml` + `scripts/make_matrix.py`; extend the matrix entries and the packaging mappings in `scripts/package_templates.py`.
