# End-user distribution decision

This document records the **chosen release architecture**. It does not claim that the native packages have passed acceptance yet.

## Windows stable-release format

The primary end-user Windows distribution will be a **64-bit, non-admin installer** built in two stages:

1. **PyInstaller one-folder application** named `SubBurn.exe`, built with the full optional feature dependency set required by the public desktop product.
2. **Inno Setup installer** wrapping that one-folder application for per-user installation under `%LOCALAPPDATA%\Programs\SubBurn`.

One-folder is intentional. Compared with a self-extracting one-file executable it gives SubBurn a more transparent file layout, avoids repeated executable unpacking on every launch, makes Tk/Tcl/native-library diagnostics easier, and reduces the number of moving parts around large native transcription dependencies.

The installer display/product name is **SubBurn**. Internal release metadata may contain a semantic version, but the normal desktop/browser product branding remains `SubBurn` without a version suffix.

### Runtime/model boundary

The desktop installer must **not bundle FFmpeg** and must **not bundle Whisper model weights**. The installed application keeps the same public runtime contract as source installs:

- use compatible system/PATH FFmpeg first;
- then a user-selected FFmpeg file/folder;
- only then download the checksum-verified managed FFmpeg runtime if needed;
- download a selected pinned transcription model only when the user explicitly prepares/uses transcription;
- reuse verified installed runtime/model data on later launches.

This avoids silently redistributing a particular FFmpeg build without an exact-build license review and avoids turning the installer into a multi-gigabyte model bundle.

### Privileges and data

The default Windows installer is **non-admin** (`PrivilegesRequired=lowest`) and installs per-user. SubBurn configuration/data/cache/state remain in platform-appropriate user locations rather than the program directory. The managed FFmpeg user-PATH promotion is also user-scoped.

### Signing

A public stable Windows build must use **Authenticode** signing for the application executable(s) and the final installer. The certificate/private key must come from the release environment or a hardware/cloud signing service and must never be committed to the repository or copied into release artifacts. Unsigned native packages may be used for engineering acceptance, but must not be called stable/public production installers.

### Native acceptance still required

Before publication, the exact installer candidate must be tested on clean supported Windows systems for install, first launch, upgrade, uninstall, non-admin behavior, long/Unicode paths, PATH changes, FFmpeg managed fallback/reuse, browser launch, transcription dependency loading, DPI/scaling, keyboard navigation, accessibility basics, and Windows Defender/SmartScreen behavior.

## Linux

For the initial public release, Linux remains a source/wheel target unless/until a native desktop package format is selected and accepted. Existing Linux/X11 source-install and real-FFmpeg tests remain part of CI/engineering evidence.

## macOS

macOS is **not to be advertised as stable support until native acceptance is completed**. If retained as a release target, the intended architecture is a signed/notarized `.app` package with the same no-bundled-FFmpeg/no-bundled-model boundary unless a later exact redistribution review approves otherwise.
