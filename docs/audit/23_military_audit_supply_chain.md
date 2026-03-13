# Audit Report 23: Binary Integrity, Dependency Hijacking & Supply Chain 

**Date:** 2026-03-13  
**Auditor:** AntiGravity Expert Systems (Doctoral Level Research & Core Architecture)  
**Clearance:** Level 5 - Military Grade Audit  
**Module:** `go.mod` / `.github/workflows`

## 1. Executive Summary
A military-grade audit assumes the adversary is not just ByteDance's engineering team, but state-sponsored actors targeting the open-source supply chain. The current CI/CD pipeline and `go.mod` structure offer basic functionality but contain zero cryptographic attestation. If a dependency is hijacked (the "SolarWinds" or `xz` vector), `douyinstream-go` becomes a globally distributed trojan.

## 2. The Vulnerability: Blind Mod Fetching
Currently, the Makefile and Github Actions simply execute `go build` or `go test`.
**The Threat:** If a third-party module (e.g., `github.com/zellyn/kooky` or a transitive logging package) is compromised by a malicious maintainer, the CI will blindly pull the malicious commit, compile it, and the Release workflow will digitally sign and distribute a trojanized binary to your users. 

## 3. The Enterprise Solutions (SLSA Level 4)

### 3.1 Strict `go.sum` Validation
The CI pipeline does not currently enforce `go.mod` and `go.sum` read-only integrity during builds.
- **Refactor:** All `go build` commands must be executed with the `-mod=readonly` flag.
- **Why:** This ensures the Go toolchain will *never* automatically update `go.mod` or fetch new dependencies attempting to bypass `go.sum` cryptographic hashes.

### 3.2 Automated Dependency Vulnerability Scanning (OSV)
- **Refactor:** Integrate `govulncheck` (Go's official vulnerability database scanner) into `.github/workflows/ci.yml`.
- **Why:** Every pull request must be scanned against the OSV (Open Source Vulnerability) database to ensure no known CVEs exist in the transitive dependency tree.

### 3.3 Reproducible Builds & Symbol Stripping
Currently, the Makefile uses:
`go build -ldflags "-s -w -X ..."`
While `-s -w` strips debugging symbols (good for binary size), it leaves absolute file paths of your local compilation machine inside the binary.
**The Threat:** Exposing local OS paths (e.g., `/home/jair/proyectos/...`) leaks environmental intelligence to reverse engineers.
**The Refactor:**
Enforce `-trimpath` on *every* compilation target.
```makefile
build:
	GOOS=$(GOOS) GOARCH=$(GOARCH) go build -trimpath -ldflags "-s -w -buildid=" -o $(BIN_NAME) ./cmd/douyinstream
```
Forcing `-buildid=` empty ensures that compiling the exact same source code on two different machines yields the exact same `SHA256` hash. This allows security auditors to independently verify that the GitHub Release binary matches the public source code exactly.

## 4. Execution Sandbox
A military-ready binary should assume it is running in a hostile environment (e.g., a shared virtual server).
- **Hardening:** We should compile with `CGO_ENABLED=0` explicitly. This guarantees a statically linked binary that does not rely on the host system's `libc.so` (which could be compromised with LD_PRELOAD rootkits intercepting system calls).
