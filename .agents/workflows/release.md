---
description: How to commit, version, and release changes for DouyinStream Go
---

# Commit, Version & Release Workflow

## Commit Convention (Conventional Commits)

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type       | When to use                              | Bumps    |
|------------|------------------------------------------|----------|
| `feat`     | New feature or capability                | MINOR    |
| `fix`      | Bug fix                                  | PATCH    |
| `refactor` | Code restructure, no behavior change     | -        |
| `perf`     | Performance improvement                  | PATCH    |
| `docs`     | Documentation only                       | -        |
| `test`     | Adding/fixing tests                      | -        |
| `ci`       | CI/CD changes                            | -        |
| `chore`    | Maintenance, deps, tooling               | -        |
| `style`    | Code style (formatting, no logic change) | -        |

### Scopes (optional)

`extractor`, `cookie`, `player`, `cli`, `http`, `config`, `platform`, `recorder`

### Examples

```bash
git commit -m "feat(extractor): add H265 dual-codec support with metadata"
git commit -m "fix(cookie): handle ttwid generation timeout"
git commit -m "refactor(cli): extract quality selection into shared function"
git commit -m "docs: update README with recording examples"
git commit -m "ci: add golangci-lint to CI pipeline"
```

### Breaking Changes

Add `!` after type or `BREAKING CHANGE:` in footer:

```bash
git commit -m "feat(extractor)!: restructure StreamResult with QualityMeta"
```

## Versioning (Semantic Versioning)

We follow [SemVer](https://semver.org/) with pre-release labels:

```
v2.MAJOR.MINOR-PRERELEASE

v2.0.0-beta.1   ← First Go rewrite (current)
v2.0.0-beta.2   ← Next batch of features
v2.0.0-rc.1     ← Release candidate (feature complete)
v2.0.0          ← Stable release → merge to main
```

### When to bump

| Change                          | Version bump         |
|---------------------------------|----------------------|
| New feature (H265, record, etc) | beta.N → beta.N+1   |
| Bug fixes only                  | beta.N → beta.N+1   |
| Feature complete, testing phase | beta.N → rc.1        |
| RC bug fixes                    | rc.N → rc.N+1        |
| Stable release                  | rc.N → v2.0.0        |

## Day-to-Day Workflow

### 1. Make changes

```bash
# Ensure you're on v2-go branch
git checkout v2-go

# Make changes...
# Build and test locally
make build
make vet
```

### 2. Commit with conventional format

```bash
git add -A
git commit -m "feat(extractor): add browser cookie extraction"
```

### 3. Push to v2-go

```bash
git push origin v2-go
# CI runs automatically (build + vet + test on 3 OSes)
```

## Release Workflow

### When ready for a new beta release:

// turbo-all

1. Update CHANGELOG.md with new entries under a new version header

2. Commit the changelog
```bash
git add CHANGELOG.md
git commit -m "chore: prepare v2.0.0-beta.2 release"
```

3. Create and push the tag
```bash
git tag -a v2.0.0-beta.2 -m "v2.0.0-beta.2: description of changes"
git push origin v2-go --tags
```

4. GoReleaser automatically creates a GitHub Release with:
   - Cross-platform binaries (5 platforms)
   - SHA256 checksums
   - Auto-generated changelog from commits

### Verify release

```bash
# Check releases page
gh release list
gh release view v2.0.0-beta.2
```

## Final Merge to Main (when stable)

```bash
# 1. Create PR from v2-go → main
gh pr create --base main --head v2-go \
  --title "v2.0.0: Complete Go rewrite" \
  --body "Full rewrite from Python to Go. See CHANGELOG.md for details."

# 2. After review, merge
gh pr merge --squash

# 3. Tag stable release on main
git checkout main
git pull
git tag -a v2.0.0 -m "v2.0.0: DouyinStream Go — Stable release"
git push origin main --tags
```

## Quick Reference

```bash
# Build
make build          # Current platform
make build-all      # All 5 platforms
make dev            # With race detector

# Quality checks
make vet            # go vet
make lint           # vet + staticcheck
make test           # Run tests
make check          # vet + tests

# Release
make release        # Build all + checksums in dist/
git tag v2.0.0-beta.N && git push --tags  # Trigger GitHub Release
```
