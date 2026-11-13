#!/usr/bin/env python3
"""Refuse to commit anything personal (generalised from zeus-options-terminal's tools/privacy_check.py).

Run automatically as a git pre-commit hook (tools/install_git_hook.sh) or by hand:
    python tools/privacy_check.py          # the staged files
    python tools/privacy_check.py --all    # every tracked and untracked file

It blocks a commit when a file
  • is a symlink, sits in a runtime-data folder, looks like a credential or database file, or is larger than 3 MB;
  • contains something shaped like a secret (API keys, tokens, JWTs, private keys, webhook URLs, Bearer headers);
  • contains YOUR identity as this computer knows it: the home-folder path, the login name, and the name and e-mail
    in the global git config. A GitHub handle inside a public URL (github.com/<handle>/…, <handle>.github.io,
    ghcr.io/<handle>/…, badges) or the noreply address is allowed.
Nothing personal is stored in this file: identities are read at run time. Problems are printed by label, never
with the matched value.
"""
from __future__ import annotations

import fnmatch
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 3 * 1024 * 1024
LARGE_OK: tuple[str, ...] = ()            # globs allowed above MAX_BYTES, e.g. ("site/assets/*.gif",)
RUNTIME_PREFIXES: tuple[str, ...] = ()    # folders the app writes at run time, e.g. ("data/", "logs/")
BAD_NAMES = re.compile(
    r"(^|/)(\.env(\..*)?|keys\.env|.*cookies?.*\.(json|txt)|.*token.*\.(json|txt)|.*secret.*|password.*|"
    r"client_(id|secret)\.(txt|json)|refresh_token.*|.*\.(pem|key|p12|pfx|sqlite3?|db))$", re.I)
ALLOWED_NAMES = re.compile(r"(^|/)\.env\.example$")
# The shapes a leaked credential takes. Named without "secret", "token" or "key": CodeQL reads such names as sensitive
# data and flags the printing of these labels (py/clear-text-logging-sensitive-data), though only the label is printed.
LEAK_SHAPES = {
    "AWS key": r"AKIA[0-9A-Z]{16}",
    "GitHub token": r"gh[pousr]_[A-Za-z0-9]{30,}",
    "OpenAI/Anthropic key": r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}",
    "Google API key": r"AIza[0-9A-Za-z_-]{35}",
    "Slack token": r"xox[baprs]-[A-Za-z0-9-]{10,}",
    "JWT / OAuth token": r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}",
    "private key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "webhook URL": r"hooks\.slack\.com/services/|discord(?:app)?\.com/api/webhooks/",
    "Bearer header": r"Bearer [A-Za-z0-9._-]{24,}",
}
SKIP_CONTENT = ("package-lock.json", "uv.lock", "poetry.lock")


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
    except Exception:
        return ""


def identity_markers() -> dict[str, str]:
    marks = {}
    home = str(Path.home())
    if len(home) > 3:
        marks["your home folder path"] = home
    try:
        import getpass
        user = getpass.getuser()
        if len(user) >= 4:
            marks["your login name"] = user
    except Exception:
        pass
    for key, label in (("user.email", "your global git e-mail"), ("user.name", "your global git name")):
        value = _git("config", "--global", "--get", key).strip()
        if len(value) >= 4 and "noreply" not in value:
            marks[label] = value
    return marks


def _public_handle_uses(text: str, handle: str, path: str = "") -> str:
    """Drop the places where a GitHub handle is public anyway: URL path segments, <handle>.github.io, noreply, the MCP
    Registry name io.github.<handle>/<repo>, and the maintainers list of Glama's claim file (glama.json)."""
    h = re.escape(handle)
    text = re.sub(rf"(?<=/){h}(?=[/.\"')\s]|$)", "", text)
    text = re.sub(rf"(?<![\w-]){h}(?=/[\w.-])", "", text)          # an OWNER/REPO slug

    text = re.sub(rf"{h}\.github\.io", "", text)
    text = re.sub(rf"\+{h}@users\.noreply\.github\.com", "", text)
    text = re.sub(rf"io\.github\.{h}/", "", text)
    if path == "glama.json" or path.endswith("/glama.json"):
        text = re.sub(r'"maintainers"\s*:\s*\[[^\]]*\]', "", text)
    return text


def staged_files() -> list[tuple[str, str]]:
    out = []
    for line in _git("diff", "--cached", "--raw", "--no-renames", "--diff-filter=ACM").splitlines():
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) >= 2:
            out.append((parts[1], path))
    return out


def all_files() -> list[tuple[str, str]]:
    out = []
    for line in _git("ls-files", "-s").splitlines():
        meta, _, path = line.partition("\t")
        out.append((meta.split()[0], path))
    for line in _git("ls-files", "--others", "--exclude-standard").splitlines():
        out.append(("100644", line))
    return out


def check(files: list[tuple[str, str]], staged: bool) -> list[str]:
    problems = []
    marks = identity_markers()
    for mode, path in files:
        if mode == "120000":
            problems.append(f"{path}: is a symlink")
            continue
        if RUNTIME_PREFIXES and path.startswith(RUNTIME_PREFIXES):
            problems.append(f"{path}: runtime data folder")
            continue
        if BAD_NAMES.search(path) and not ALLOWED_NAMES.search(path):
            problems.append(f"{path}: looks like a credential or data file")
            continue
        if staged:
            blob = subprocess.run(["git", "show", f":{path}"], cwd=ROOT, capture_output=True).stdout
        else:
            p = ROOT / path
            blob = p.read_bytes() if p.is_file() else b""
        if len(blob) > MAX_BYTES and not any(fnmatch.fnmatch(path, g) for g in LARGE_OK):
            problems.append(f"{path}: larger than {MAX_BYTES // (1024 * 1024)} MB")
        if path.endswith(SKIP_CONTENT):
            continue
        text = blob.decode("utf-8", "ignore")
        for label, pattern in LEAK_SHAPES.items():
            if re.search(pattern, text):
                problems.append(f"{path}: contains a {label}")
        for label, value in marks.items():
            seen = _public_handle_uses(text, value, path) if label == "your global git name" else text
            if value and value in seen:
                problems.append(f"{path}: contains {label}")
    return problems


def main() -> int:
    every = "--all" in sys.argv
    files = all_files() if every else staged_files()
    problems = check(files, staged=not every)
    if problems:
        print("✋ privacy check failed — nothing was committed:" if not every else "✋ privacy check found:")
        for p in problems:
            print("   •", p)
        print("Fix or unstage these files. (Bypass only if you are sure: git commit --no-verify)")
        return 1
    print(f"✓ privacy check passed ({len(files)} file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
