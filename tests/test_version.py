"""A release takes the version from pyproject.toml; everything that shows the version has to agree with it, and the
README must still work on PyPI. Copied from the maintaining-github-repos skill; adjust the names at the top."""

from __future__ import annotations

import importlib
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODULE = "talite"                      # the import name; its __version__ must match pyproject.toml
DIST = "tradingagents-lightweight"                          # the name on PyPI
BADGE = None                               # the READMEs use a dynamic PyPI badge, nothing to keep in step
ZH_CHANGELOG = next((p for p in ("docs/zh/CHANGELOG.md", "CHANGELOG_zh.md") if (ROOT / p).exists()), None)


def _release_notes():
    spec = importlib.util.spec_from_file_location("release_notes", ROOT / "scripts" / "release_notes.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_version_agrees_everywhere():
    rn = _release_notes()
    version = rn.project_version(ROOT)
    assert importlib.import_module(MODULE).__version__ == version
    for log in ("CHANGELOG.md", ZH_CHANGELOG):
        if log is None:
            continue
        newest = re.search(r"^## (\d+\.\d+\.\d+)", (ROOT / log).read_text(encoding="utf-8"), re.M)
        assert newest and newest.group(1) == version, f"{log}: the newest section is not {version}"
    if (ROOT / "CITATION.cff").exists():
        assert f'version: "{version}"' in (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    for readme in ("README.md", "README.zh-CN.md"):
        if not (ROOT / readme).exists():
            continue
        text = (ROOT / readme).read_text(encoding="utf-8")
        if BADGE:
            assert BADGE.format(version=version) in text, f"{readme} version badge"
        if "@software{" in text:
            assert f"version = {{{version}}}" in text, f"{readme} BibTeX version"


def test_release_notes_link_to_the_tag():
    rn = _release_notes()
    version = rn.project_version(ROOT)
    text = rn.notes(version, ROOT, "Owner/Repo")
    tag = f"v{version}"
    assert rn.changelog_section(version, ROOT).splitlines()[0][:40] in text
    links = re.findall(r"\]\(([^)\s]+)\)", text) + re.findall(r'src="([^"]+)"', text)
    assert all(re.match(r"^(https?:|#)", u) for u in links), "every link and picture is absolute"
    assert f"pip install {DIST}=={version}" in text
    assert f"docker pull ghcr.io/owner/repo:{version}" in text, "image names are lowercase"
    prev = rn.previous_version(version, ROOT)
    if prev:
        assert f"https://github.com/Owner/Repo/compare/v{prev}...{tag}" in text
    if ZH_CHANGELOG and getattr(rn, "BILINGUAL", False):
        english, _, chinese = text.partition("\n---\n")
        assert chinese and re.search(r"[\u4e00-\u9fff]", chinese), "the Chinese section follows ---"


def test_both_changelogs_list_the_same_versions():
    if ZH_CHANGELOG is None:
        pytest.skip("no Chinese changelog")
    heads = [re.findall(r"^## +(\d+\.\d+\.\d+)\b", (ROOT / f).read_text(encoding="utf-8"), re.M)
             for f in ("CHANGELOG.md", ZH_CHANGELOG)]
    assert heads[0] == heads[1], "both changelogs list the same versions, newest first"
    key = lambda v: tuple(int(x) for x in v.split("."))  # noqa: E731
    assert heads[0] == sorted(set(heads[0]), key=key, reverse=True), "newest first, no duplicates"


def test_the_pypi_readme_has_only_absolute_links():
    """PyPI shows README.md on its own; the build rewrites its relative links and images (pyproject.toml)."""
    tomllib = pytest.importorskip("tomllib")
    meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    hook = meta.get("tool", {}).get("hatch", {}).get("metadata", {}).get("hooks", {}).get("fancy-pypi-readme")
    if hook is None:                               # setuptools ships README.md as it is
        text = (ROOT / meta["project"]["readme"]).read_text(encoding="utf-8")
    else:
        text = "".join((ROOT / f["path"]).read_text(encoding="utf-8") for f in hook["fragments"])
        for s in hook.get("substitutions", []):
            text = re.sub(s["pattern"], s["replacement"], text)
    assert not re.findall(r"\]\((?!https?:|mailto:)[^)\s]+\)", text)
    assert not re.findall(r'(?:src|href)="(?!https?:|mailto:)[^"]*"', text)
