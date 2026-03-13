# Audit Report 07: CI/CD Pipeline & Build Safety

**Date:** 2026-03-13  
**Auditor:** AntiGravity Expert Systems  
**Module:** GitHub Actions (`.github/workflows/`) & Makefiles

## 1. Executive Summary
The continuous integration pipeline establishes a robust baseline for testing and distributing multi-platform binaries automatically via `GoReleaser`. However, there are architectural discrepancies between the local developer experience (via `Makefile`) and the CI pipeline (`ci.yml`), which will invariably cause developer friction as "It works on my machine" fails in the automated checks.

## 2. Findings: Developer vs. CI Divergence (Severity: Medium)

### 2.1 The Linter Mismatch
**Context:** In the `Makefile`, the `lint` target executes `staticcheck` (`staticcheck ./...`). However, in `.github/workflows/ci.yml`, the pipeline runs `golangci-lint-action@v6`.
**Gap:** `golangci-lint` is an aggregator that runs dozens of linters by default (including `govet`, `errcheck`, `ineffassign`). `staticcheck` is far less strict.
- A contributor running `make lint` locally will pass all tests perfectly.
- Upon opening a Pull Request to `v2-go`, `golangci-lint` will fail abruptly because of unhandled errors (e.g., `_ = os.WriteFile` in `extractor.go`, which violates `errcheck`).
**Recommendation:** Standardize tooling. Have the `Makefile` install and run `golangci-lint` identically to the CI server, ensuring identical standards across all environments. Add a `.golangci.yml` file to the repository root to define the strictness explicitly.

## 3. Findings: Pipeline Inefficiencies (Severity: Low)

### 3.1 Loop Artifacting in Cross-Compile Job
**Context:** In `ci.yml`, the `cross-compile` job iterates sequentially:
```bash
  for platform in "${platforms[@]}"; do
    GOOS="${platform%/*}" GOARCH="${platform#*/}" \
      go build -trimpath -o /dev/null ./cmd/douyinstream
  done
```
**Gap:** This script fails the job at the *bash level* if a platform fails to compile, without clearly delineating in the GitHub Actions UI which target platform specifically broke. It also wastes execution time sequentially building rather than farming it out to GitHub's parallel runners.
**Recommendation:** Refactor the `cross-compile` job to utilize GitHub Actions `matrix` strategy just like the OS matrix for testing, explicitly splitting `[linux/amd64, darwin/arm64, windows/amd64, ...]` across distinct execution parallel jobs.

### 3.2 Hardcoded Go Versions (Go 1.22 vs 1.25)
**Context:** The project uses `go 1.22` statically mapped in `ci.yml`, but `mod.go` (and your local setup indicated) is aiming for the bleeding-edge compiler architectures (1.24/1.25 natively support better GC for streams).
**Recommendation:** Replace hardcoded `'1.22'` values in `.github` with `stable` matching the `go.mod` declaration to prevent future syntactic discrepancies when newer concurrency primitives or `iter` packages are integrated.
