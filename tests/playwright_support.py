from __future__ import annotations
import os
import shutil


def launch_chromium(playwright, *, args=None, headless=True):
    """Launch system Chromium when present, otherwise Playwright's managed Chromium."""
    executable = (
        os.environ.get('SUBBURN_CHROMIUM_EXECUTABLE')
        or shutil.which('chromium')
        or shutil.which('chromium-browser')
        or shutil.which('google-chrome')
    )
    kwargs = {'headless': bool(headless), 'args': list(args or [])}
    if executable:
        kwargs['executable_path'] = executable
    return playwright.chromium.launch(**kwargs)
