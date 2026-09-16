# Windows packaging staging

This directory contains the committed contract for the future native Windows package. The exact PyInstaller/Inno Setup build must run on a native Windows release runner and **must not be called stable** until the Windows acceptance matrix passes.

## Intended pipeline

1. Create a clean Python 3.13 release environment from the reviewed `uv.lock` with the `full` feature set.
2. Build a **PyInstaller one-folder** GUI application named `SubBurn.exe` (windowed/no console).
3. Launch and exercise that exact frozen tree before wrapping it.
4. Instantiate `SubBurn.iss.in` with the exact release version/build directory and compile it with **Inno Setup**.
5. The frozen application executable(s) and final installer **must be signed** with Authenticode using release-environment credentials. Signing material must never enter the repository.
6. Install as a standard **non-admin** user, run native acceptance, restart Windows where relevant to PATH behavior, upgrade from the previous installer candidate, then uninstall and verify cleanup boundaries.

The installer does not include FFmpeg binaries or transcription model weights. Those remain verified/on-demand runtime assets under SubBurn's existing provenance policy.

The Inno template can be rendered deterministically after the frozen application exists:

```powershell
python scripts/render_windows_installer.py --version 2.8.0 --app-dir C:\build\SubBurn --output build\SubBurn.iss
```

The first native package acceptance should use a clean full-feature environment and a **PyInstaller `--onedir --windowed`** build. Because transcription and drag/drop are dynamically imported/contain native components, the exact `--collect-all`/hook set must be proven on Windows before it is committed as the stable automated packager; this repository deliberately does not pretend that an unexecuted PyInstaller spec is accepted.

A future Windows packaging workflow may automate these steps only after the first manual/native packaging run proves the exact PyInstaller hidden-import/native-DLL set and Inno behavior.
