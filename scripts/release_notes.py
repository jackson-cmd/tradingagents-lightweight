"""Release notes for one version, in both languages, with links that work on the release page.

    python scripts/release_notes.py 1.2.3      # the notes for v1.2.3
    python scripts/release_notes.py --version  # the version in pyproject.toml

The release workflow (.github/workflows/release.yml) runs it when a new version reaches main. The notes are:
a line of links (website, all changes since the previous version), the version's section of CHANGELOG.md, a line
`---`, the same section of the Chinese changelog, and the install lines. Relative links and pictures in the
changelogs point into the repository; on a release page they would break, so they become links to the files as
they were at that version's tag. (ZEUS puts both languages into its notes the same way; set BILINGUAL = False for an
English-only release with a link to the Chinese changelog, as RTA does.)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = os.environ.get("GITHUB_REPOSITORY", "jackson-cmd/tradingagents-lightweight")
DIST = "tradingagents-lightweight"  # the name on PyPI
WEBSITE = ""  # "" when there is no website
BILINGUAL = True
# where the Chinese changelog lives: docs/zh/CHANGELOG.md (RTA) or CHANGELOG_zh.md (ZEUS)
ZH_CHANGELOG = next((p for p in ("docs/zh/CHANGELOG.md", "CHANGELOG_zh.md") if (ROOT / p).exists()), None)
HEADING = r"^## +(\d+\.\d+\.\d+)\b"  # matches "## 1.2.3 (2026-11-12)" and "## 1.2.3（2026-11-12）"


def project_version(root: Path = ROOT) -> str:
    m = re.search(r'^version\s*=\s*"([^"]+)"', (root / "pyproject.toml").read_text(encoding="utf-8"), re.M)
    if not m:
        raise SystemExit("pyproject.toml has no version")
    return m.group(1)


def section(version: str, file: str = "CHANGELOG.md", root: Path = ROOT) -> str:
    text = (root / file).read_text(encoding="utf-8")
    parts = re.split(HEADING + r"[^\n]*\n", text, flags=re.M)
    found = dict((parts[i], parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2))
    if version not in found:
        raise SystemExit(f"{file} has no section for {version}")
    return found[version]


def changelog_section(version: str, root: Path = ROOT) -> str:
    return section(version, "CHANGELOG.md", root)


def absolute_links(text: str, tag: str, repo: str = REPO) -> str:
    def link(m: re.Match) -> str:
        target = m.group(2)
        if re.match(r"^(https?:|mailto:|#)", target):
            return m.group(0)
        return f"{m.group(1)}(https://github.com/{repo}/blob/{tag}/{target.removeprefix('./')})"

    text = re.sub(r"(\[[^\]]*\])\(([^)\s]+)\)", link, text)
    return re.sub(r'src="(?!https?:)(?:\./)?([^"]+)"', lambda m: f'src="https://github.com/{repo}/raw/{tag}/{m.group(1)}"',
                  text)


def previous_version(version: str, root: Path = ROOT) -> str | None:
    """The highest version in the changelog below this one."""
    heads = re.findall(HEADING, (root / "CHANGELOG.md").read_text(encoding="utf-8"), re.M)
    key = lambda v: tuple(int(x) for x in v.split("."))  # noqa: E731
    lower = [v for v in heads if key(v) < key(version)]
    return max(lower, key=key) if lower else None


def notes(version: str, root: Path = ROOT, repo: str = REPO) -> str:
    tag = f"v{version}"
    links = []
    if WEBSITE:
        links.append(f"[Website]({WEBSITE})")
    prev = previous_version(version, root)
    if prev:
        links.append(f"[All changes since v{prev}](https://github.com/{repo}/compare/v{prev}...{tag})")
    parts = [" · ".join(links)] if links else []
    parts.append(absolute_links(changelog_section(version, root), tag, repo))
    zh = ZH_CHANGELOG if (root / ZH_CHANGELOG if ZH_CHANGELOG else root / "-").exists() else None
    if BILINGUAL and zh:
        parts.append("---")
        parts.append(absolute_links(section(version, zh, root), tag, repo))
    elif zh:
        parts.append(f"中文更新记录：[{zh}](https://github.com/{repo}/blob/{tag}/{zh})")
    image = f"ghcr.io/{repo.lower()}"  # image names must be lowercase; metadata-action lowercases, docker pull does not
    parts.append(f"Install this version: `pip install {DIST}=={version}` · Docker: `docker pull {image}:{version}`")
    return "\n\n".join(parts) + "\n"


def main(argv: list[str]) -> None:
    if argv[1:2] == ["--version"]:
        print(project_version())
        return
    print(notes(argv[1] if len(argv) > 1 else project_version()), end="")


if __name__ == "__main__":
    main(sys.argv)
