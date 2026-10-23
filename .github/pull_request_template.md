## What does this pull request do?

<!-- A short description of the change. -->

## Type of change

- [ ] Bug fix (PATCH)
- [ ] New feature (MINOR)
- [ ] Breaking change (MAJOR) — node id, `RETURN_TYPES` or widget order changed
- [ ] Documentation / tests only

## Related issue

<!-- Closes #123 -->

## How was it tested?

<!--
The test suite runs automatically on every push and pull request
(Windows + Linux, Python 3.12 and 3.13).

Describe what you did manually, if anything.
-->

- [ ] `python -m pytest tests/ -v` passes locally
- [ ] Tested in a real ComfyUI instance

## Checklist

- [ ] The version will be bumped with `python tools/release.py patch|minor|major`
      (or the PR targets `main` / `develop` and the release script handles it)
- [ ] `CHANGELOG.md` was updated
- [ ] New nodes keep the existing `RETURN_TYPES` (old graphs must keep working)
- [ ] New widgets are appended at the **end** of the optional block
- [ ] No secret was added to the repository (salt, manifest, keys)
- [ ] The docs were updated (`README.md`, and the node docstring when relevant)

## Screenshots

<!-- If the change touches the node UI, paste a screenshot here. -->
