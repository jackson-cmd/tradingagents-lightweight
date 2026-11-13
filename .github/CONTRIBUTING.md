# Contributing / 参与贡献

Thanks for helping. Bug reports, fixes, features, docs and translations are all welcome.
感谢参与！问题反馈、修复、新功能、文档和翻译都非常欢迎。

Please follow the [code of conduct](CODE_OF_CONDUCT.md). 参与时请遵守[行为准则](CODE_OF_CONDUCT.md)。

## Setup / 开发环境

```bash
git clone https://github.com/jackson-cmd/tradingagents-lightweight
cd tradingagents-lightweight
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
tools/install_git_hook.sh   # privacy check before every commit / 每次提交前自动做隐私检查
pytest
ruff check .
```

## Ground rules / 基本原则

- Tests run offline. Mock network calls; mark anything that needs the internet with `@pytest.mark.network`.
  测试必须能离线运行。网络请求用 mock，需要联网的测试加 `@pytest.mark.network`。
- No secrets, account numbers, personal data or local paths in code, tests, logs or screenshots. The pre-commit hook checks.
  代码、测试、日志和截图里不能出现密钥、账户号、个人信息或本机路径，提交钩子会检查。
- Keep user-facing text in both languages: README.md / README.zh-CN.md and CHANGELOG.md / CHANGELOG_zh.md.
  面向用户的文字请同时更新中英文：两份 README（README.md、README.zh-CN.md）和两份更新记录（CHANGELOG.md、CHANGELOG_zh.md）。
- One change per pull request; open an issue first for anything users will notice.
  一个 PR 只做一件事；用户能感觉到的改动请先开 issue。

## Releasing / 发布新版本

1. In the pull request, raise the version (`pyproject.toml` and `talite/__init__.py`), add its section at the top of `CHANGELOG.md` and the Chinese changelog, and, if the READMEs use a static version badge, update it in both. `tests/test_version.py` fails if any of them disagree.
   在 PR 里提高版本号（`pyproject.toml` 和 `talite/__init__.py`），在两份更新记录最上面加上这一版的说明，两份 README 如果用的是静态版本徽章，也要一起改；有一处对不上，`tests/test_version.py` 就会失败。
2. Merge it. When CI passes on main, `.github/workflows/release.yml` drafts the release with that changelog section, attaches the wheel and the source archive, pushes the Docker image `ghcr.io/jackson-cmd/tradingagents-lightweight` (`X.Y.Z`, `X.Y`, `latest`), publishes the release and uploads to PyPI. Nothing else to do.
   合并即可。main 上的 CI 通过后，`.github/workflows/release.yml` 会用那一节更新说明建草稿、附上 wheel 和源码包、推送 Docker 镜像 `ghcr.io/jackson-cmd/tradingagents-lightweight`（`X.Y.Z`、`X.Y`、`latest`），然后正式发布并上传 PyPI，不用手动操作。
3. PyPI trusts this workflow (trusted publisher: workflow `release.yml`, environment `pypi`) while the repository variable `PYPI_PUBLISH` is `true`. A version number can go to PyPI only once. To publish an existing release again: `gh workflow run release.yml -f tag=vX.Y.Z` (add `-f rebuild_image=true` to push its image again).
   仓库变量 `PYPI_PUBLISH` 为 `true` 时，PyPI 信任这个工作流（可信发布者：工作流 `release.yml`，环境 `pypi`）。同一个版本号只能传一次 PyPI。要重新发布已有的版本：`gh workflow run release.yml -f tag=vX.Y.Z`（加 `-f rebuild_image=true` 会重新推送镜像）。
