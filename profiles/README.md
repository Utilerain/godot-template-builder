# Build profile

This folder holds the **build profile** — the file that tells the compiler what to strip out of the engine when building the custom export templates.

## How to create a profile (inside Godot)

> The editor dialog is available since **Godot 4.5**. On older versions, write the JSON file by hand (see the format below).

1. Open any project in Godot (the profile is created per project).
2. Menu: **Project → Tools → Engine Compilation Configuration Editor**.
3. Uncheck the features you don't need — for example 3D classes (`Node3D` and its descendants), physics, navigation, XR or audio, if your projects never use them.
   The **Detect from Project** button automatically detects what the project actually uses and disables the rest — start with it, then review the result manually.
4. **Save As** → save the file into this folder as `build_profile.json`.
5. **Commit the file** — CI builds the templates from it.

The file format is JSON (the editor suggests the `.gdbuild` extension by default).
If you saved it as `.gdbuild`, either rename it to `build_profile.json` or leave it as is: the CI script automatically picks up a sibling `.gdbuild` when the `.json` file is not found.

## Important

- Classes disabled in the profile are **physically removed from the templates at compile time**: if an exported project uses such a class, the game will crash at runtime. Test the project before building the templates.
- If `build_profile.json` (or `.gdbuild`) is not found, CI builds the templates with the **standard feature set** and warns about it in the log and the release notes — the build does not fail.

## Format (reference)

The file is passed to SCons via the `build_profile=` option (see Godot's `SConstruct`):

```json
{
  "type": "build_profile",
  "disabled_build_options": {
    "module_openxr_enabled": false,
    "disable_xr": true
  },
  "disabled_classes": ["AESContext", "ZIPReader"]
}
```

- `disabled_build_options` — SCons build option values (disables modules and features);
- `disabled_classes` — names of Godot classes that will not make it into the binaries.
