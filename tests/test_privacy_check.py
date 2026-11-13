"""tools/privacy_check.py: uses of the GitHub handle that are public by design pass; the same name anywhere else
is still caught."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HANDLE = "someone-example"


def _check():
    spec = importlib.util.spec_from_file_location("privacy_check", ROOT / "tools" / "privacy_check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._public_handle_uses


def test_public_uses_of_the_handle_pass():
    public = _check()
    assert HANDLE not in public(f"https://github.com/{HANDLE}/repo and ghcr.io/{HANDLE}/repo", HANDLE, "README.md")
    assert HANDLE not in public(f'"name": "io.github.{HANDLE}/repo"', HANDLE, "server.json")
    assert HANDLE not in public(f'{{"maintainers": ["{HANDLE}"]}}', HANDLE, "glama.json")


def test_the_same_name_elsewhere_is_still_caught():
    public = _check()
    assert HANDLE in public(f'{{"maintainers": ["{HANDLE}"]}}', HANDLE, "package.json")
    assert HANDLE in public(f'{{"maintainers": ["{HANDLE}"], "author": "{HANDLE}"}}', HANDLE, "glama.json")
    assert HANDLE in public(f"Written by {HANDLE}.", HANDLE, "notes.md")
