# Security policy

## Supported versions

SubBurn is currently pre-release software. Security fixes are applied to the latest development line only until the first stable release policy is published.

## Reporting a vulnerability

Please **do not** disclose suspected vulnerabilities, exploit details, private paths, tokens, media, or diagnostic bundles in a public issue.

For the public GitHub repository, use **Security → Report a vulnerability** so the report is handled through GitHub private vulnerability reporting.

If private vulnerability reporting is not available, do not post sensitive technical details publicly. Open a minimal issue stating only that you need a private security-reporting channel; a maintainer can then enable or provide the appropriate private path.

Useful reports include:

- affected SubBurn version / commit;
- operating system and installation type;
- affected component (desktop UI, localhost dashboard, FFmpeg/runtime handling, transcription, queue/recovery, packaging);
- minimal reproduction steps using non-sensitive fixtures;
- impact and preconditions;
- whether the issue is remotely reachable or requires local access;
- suggested remediation, if known.

Do not attach real private videos, subtitles, credentials, browser data, model tokens, or unredacted diagnostic archives.

## Scope notes

The browser dashboard is intentionally loopback-only and uses a per-run authenticated session. Reports showing a path from an untrusted origin/process to privileged local actions are security-relevant.

Third-party vulnerabilities in FFmpeg, Python packages, transcription runtimes, model-hosting infrastructure, or operating-system components should still be reported when SubBurn's integration makes them exploitable in a way that SubBurn can mitigate.

## Disclosure

Please allow maintainers reasonable time to validate and remediate a report before public disclosure. No fixed response SLA is promised for this volunteer open-source project.
