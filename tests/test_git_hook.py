"""tools/install_git_hook.sh puts the privacy check where git runs it: from the main checkout and from a worktree
(whose .git is a file), never into a folder set by core.hooksPath, and without losing a hook that was already there.
Adapted from zeus-options-terminal's tests/test_git_hook.py (PR #62 and #63)."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(sys.platform == "win32" or not shutil.which("bash") or not shutil.which("git"),
                                reason="the installer is a shell script for macOS and Linux")


def run(cwd, *cmd, check=True):
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
    return subprocess.run(list(cmd), cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8",
                          check=check)


@pytest.fixture
def repo(tmp_path):
    """A small repository holding the two tools, and a worktree of it on its own branch."""
    main = tmp_path / "main"
    (main / "tools").mkdir(parents=True)
    for name in ("install_git_hook.sh", "privacy_check.py"):
        shutil.copy2(ROOT / "tools" / name, main / "tools" / name)
    (main / "README.md").write_text("hello\n", encoding="utf-8")
    run(main, "git", "init", "-q")
    run(main, "git", "add", "-A")
    run(main, "git", "commit", "-q", "-m", "start")
    run(main, "git", "worktree", "add", "-q", "-b", "feature", str(tmp_path / "wt"))
    return main, tmp_path / "wt"


def test_installs_from_a_worktree_and_blocks_a_key_file_there(repo):
    main, wt = repo
    run(wt, "bash", "tools/install_git_hook.sh")
    hook = main / ".git" / "hooks" / "pre-commit"            # the folder every worktree shares
    assert hook.is_file() and os.access(hook, os.X_OK)
    assert "tools/privacy_check.py" in hook.read_text(encoding="utf-8")
    (wt / "keys.env").write_text("TOKEN=x\n", encoding="utf-8")
    run(wt, "git", "add", "keys.env")
    commit = run(wt, "git", "commit", "-q", "-m", "oops", check=False)
    assert commit.returncode != 0
    assert "privacy check failed" in commit.stdout + commit.stderr


def test_installs_from_the_main_checkout_and_replaces_an_older_privacy_hook(repo):
    """A hook written by an earlier version of the installer is ours: it is replaced, never kept as pre-commit.local."""
    main, _ = repo
    hooks = main / ".git" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    (hooks / "pre-commit").write_text('#!/bin/sh\nexec python3 "$(git rev-parse --show-toplevel)/tools/privacy_check.py"\n',
                                      encoding="utf-8")
    run(main, "bash", "tools/install_git_hook.sh")
    run(main, "bash", "tools/install_git_hook.sh")
    assert (hooks / "pre-commit").is_file()
    assert not (hooks / "pre-commit.local").exists()


def test_a_checkout_without_the_check_still_commits(repo):
    """Branches made before the check existed must still be able to commit; the hook says it skipped."""
    _, wt = repo
    run(wt, "bash", "tools/install_git_hook.sh")
    run(wt, "git", "rm", "-q", "tools/privacy_check.py")
    commit = run(wt, "git", "commit", "-q", "-m", "no check here")
    assert "skipped" in commit.stdout + commit.stderr


def test_leaves_a_core_hooks_path_folder_alone_and_says_so(repo, tmp_path):
    main, _ = repo
    shared = tmp_path / "shared-hooks"
    run(main, "git", "config", "core.hooksPath", str(shared))
    out = run(main, "bash", "tools/install_git_hook.sh")
    assert not shared.exists()
    assert (main / ".git" / "hooks" / "pre-commit").is_file()
    assert "core.hooksPath" in out.stderr


def test_keeps_an_existing_hook_and_still_runs_it(repo):
    main, wt = repo
    old = main / ".git" / "hooks" / "pre-commit"
    old.write_text("#!/bin/sh\necho old-hook-ran\n", encoding="utf-8")
    old.chmod(0o755)
    run(main, "bash", "tools/install_git_hook.sh")
    assert (main / ".git" / "hooks" / "pre-commit.local").is_file()
    (wt / "notes.txt").write_text("fine\n", encoding="utf-8")
    run(wt, "git", "add", "notes.txt")
    commit = run(wt, "git", "commit", "-q", "-m", "fine")
    assert "old-hook-ran" in commit.stdout + commit.stderr
