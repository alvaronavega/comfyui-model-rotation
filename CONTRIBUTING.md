# Contributing

Thanks for helping out! This project follows a **gitflow** workflow, and every
change goes through the automated test suite before it lands.

## The branches

```
main        production — only tagged releases live here
develop     integration — the branch every change ends up in
feature/*   a new feature, branched from develop
release/*   release preparation, branched from develop
hotfix/*    an urgent fix, branched from main
```

| Branch | Merges into | Gets a tag? |
|--------|-------------|-------------|
| `feature/*` | `develop` | no |
| `release/*` | `main` **and** `develop` | yes (`vX.Y.Z`) |
| `hotfix/*` | `main` **and** `develop` | yes (`vX.Y.Z`) |

`main` and `develop` are **protected**: no direct push, the CI must be green
and one approval is required.

## The everyday loop

```bash
# 1. branch off develop
python tools/gitflow.py feature add-my-feature
#    (or: git checkout develop && git checkout -b feature/add-my-feature)

# 2. write the code, add tests
python -m pytest tests/ -v

# 3. commit and push
git add -A
git commit -m "feat: add my feature"
git push -u origin feature/add-my-feature

# 4. open a pull request targeting develop
#    (gh pr create --base develop --fill)

# 5. when the PR is merged, clean up the branch
python tools/gitflow.py finish feature/add-my-feature
```

## Releasing

```bash
# from develop
python tools/gitflow.py release 2.1.0
python tools/release.py set 2.1.0
# ... fix whatever is needed on the release branch ...

python tools/gitflow.py finish release/2.1.0
#    -> merges into main, creates the tag v2.1.0, merges main back into develop

git push origin main develop v2.1.0
```

### The semantic policy

| Bump | When |
|------|------|
| **MAJOR** | a node class id is removed or renamed, a `RETURN_TYPES` changes, or the widget order changes (existing graphs stop working) |
| **MINOR** | a new node, a new widget or a new option is added |
| **PATCH** | a bug fix, documentation, tests or an internal refactor |

## The version

The version is derived from the git history (`git describe`), so it always
tells you exactly which code produced a file:

```
2.0.0                 on the tag v2.0.0, clean tree
2.0.0+21.gd8477fc      21 commits after the tag
2.0.0+21.gd8477fc.dirty  ... with uncommitted changes
```

On the development branches the version carries a prerelease label:

| Branch | Version |
|--------|---------|
| `main` | `2.0.0` |
| `develop` | `2.1.0-dev.5` |
| `feature/add-foo` | `2.1.0-feature.add-foo.2` |
| `release/2.1.0` | `2.1.0-rc.1` |
| `hotfix/fix-bar` | `2.0.1-hotfix.fix-bar.1` |

## The test suite

```bash
python -m pip install pytest numpy pillow
python -m pytest tests/ -v
```

The tests need **no ComfyUI and no GPU** — `folder_paths` and `comfy.sd` are
stubbed in `tests/conftest.py`.

The CI runs the suite on **Windows and Linux**, with **Python 3.12 and 3.13**,
on every push and pull request.

## House rules

* **Never break an existing graph.** Node class ids, `RETURN_TYPES` and the
  order of the existing widgets must not change without a MAJOR bump.
* **New widgets go at the end** of the optional block, so the widget indices
  of the old ones stay valid.
* **Every behaviour change comes with a test.**
* **No secrets in the repository.** The salt (`utils/secure_config.json`) and
  the language preference are git-ignored; the manifest lives outside the repo.
* **Update `CHANGELOG.md`** and the node docstring when the behaviour changes.
