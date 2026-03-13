# Audit Report 24: Execution Sandbox - DLL Hijacking & Path Traversal (RCE)

**Date:** 2026-03-13  
**Auditor:** AntiGravity Expert Systems (Doctoral Level Research & Core Architecture)  
**Clearance:** Level 5 - Military Grade Audit  
**Module:** `cmd/douyinstream/main.go` / `internal/player`

## 1. Executive Summary
A military-grade code review demands an analysis of Local Privilege Escalation (LPE) and Remote Code Execution (RCE) vectors. `douyinstream-go` relies heavily on external binaries (`mpv`, `ffmpeg`) via `os/exec`. In environments where the CLI is deployed automatically (e.g., servers, automated scrapers, CI/CD runners), this represents a critical vulnerability surface known as "Path Hijacking".

## 2. The Vulnerability: Blind `PATH` Resolution
Currently, the codebase executes `exec.LookPath("ffmpeg")` and subsequently `exec.CommandContext(ctx, ffmpegPath, args...)`.

**The Threat (CVE-2020-36528 / Unsafe Lookups):**
On Windows, if the Current Working Directory (CWD) is searched before the global `%PATH%` (a common behavior in older Go versions or specific shell environments), an attacker can drop a malicious `ffmpeg.exe` file into the folder where `douyinstream` is executed.
- If the user types `douyinstream record https://live.douyin.com...`
- The Go binary resolves the malicious local `ffmpeg.exe` instead of the system one.
- The attacker achieves arbitrary code execution with the permissions of the user running `douyinstream` (potentially Administrator).

On Linux, if the attacker can modify the `$PATH` variable of the service account running the scraping daemon, they can redirect `douyinstream` to execute a rootkit bash script named `ffmpeg`.

## 3. The Defense: The Cryptographic Execution Vault

### 3.1 Hardened Path Execution
`douyinstream-go` must cease trusting the environment it operates within.
- **Refactor:** Implement a Whitelist of allowed Absolute Paths `/usr/bin/ffmpeg`, `/usr/local/bin/ffmpeg`, `C:\Program Files\ffmpeg...`.
- Do not blindly pass raw user input from global Flags (`--player mpv`) directly into the `.Path` attribute of `exec.Cmd()`. The application must assert that the resolved executable exists exactly within the system's protected binary directories.

### 3.2 Binary Signature & Hash Verification
A military-grade daemon does not execute any binary without verifying its integrity hash.
If we implement the Go-native DVR (Report 11), we eliminate the `ffmpeg` threat entirely. However, if `mpv` remains for playback:
- **Refactor:** The configuration file (`config.toml`) should store the expected `SHA256` hash of the `mpv` binary on the host machine.
- Before `exec.CommandContext()` runs, a Go routine computes `sha256sum(/usr/bin/mpv)` and compares it against the trusted config. If it mismatches, it kills the process, preventing trojanized media players from reading the private stream data or installing ransomware in the background.

## 4. The `args...` Injection Vector
Currently, the player construction logic appends user-provided URLs or Flags directly into the string slice passed to `exec.Command()`.
- **Refactor Check:** Ensure absolutely no user-provided string (like the Douyin live chat or room title) can ever break out of the string slice and inject a shell argument (e.g., `; rm -rf /`).
- Go's `os/exec` avoids shell injection by passing arguments directly to the Kernel (`execve`), bypassing `/bin/sh`. This is a strong positive, but developers must be explicitly trained never to wrap `ffmpeg` commands in `bash -c` strings in future feature expansions.
