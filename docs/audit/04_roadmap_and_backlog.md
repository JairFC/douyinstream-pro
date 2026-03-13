# Audit Report 04: Roadmap & Actionable Backlog

**Date:** 2026-03-13  
**Auditor:** AntiGravity Expert Systems  
**Module:** Project Management

## 1. Executive Summary
The migration to Go v2.0.0-beta.1 is structurally sound but functionally incomplete for production release against a volatile streaming platform like Douyin. The audit identifies a clear priority of tasks to move from a "beta CLI" to an "Enterprise Quality Client".

## 2. Priority Backlog (Action Items)

### 🔥 P0: Critical Vulnerability Remediation
**These must be fixed before v2.0.0 Stable**
- [ ] **Remove Hardcoded Anti-Bot Tokens:** `__ac_nonce` and `odin_tt` in `internal/cookie/cookie.go` must be dynamically resolved or safely generated.
- [ ] **Implement Local Browser Cookie Extraction:** Add support for querying a user's local Chrome/Edge SQLite databases (via a library like `kooky`) to fetch authenticated `v.douyin.com` cookies, replacing the reliance entirely on spoofing.
- [ ] **Stabilize HTML Parsing:** Swap the string slicing (`"__pace_f"`) mechanism in `parsePaceData()` to an AST tokenizer or a robust RegEx to prevent silent extraction failures during UI updates.

### 🟡 P1: Reliability & Performance Core
**These turn a scripting project into a daemon-level tool**
- [ ] **DVR Resiliency Loop:** The `recordCmd` must wrap `ffmpeg` (or native Go `io.Copy`) in a reconnect loop that re-extracts the FLV URL continuously upon socket drop to guarantee complete multi-hour recordings.
- [ ] **Wire Up Configuration Layer:** Integrate `viper` parsing to hydrate `config.Config` from a `config.toml` file. Pass the config down to dependencies via Dependency Injection instead of relying on default constants.
- [ ] **MPV Low-Latency Mode:** Hardcode or configure low-latency arguments for MPV (`--profile=low-latency`) when streaming. A 30s VOD cache on a live socket creates massive artificial delay.

### 🟢 P2: Expansion & Testing
**Long-term Maintainability**
- [ ] **Encapsulate Global CLI Variables:** Move `flagQuality`, `flagPlayer` to respective Command Options structs, allowing for fully parallelizable unit testing of the CLI runtime.
- [ ] **JavaScript Interpreter (X-Bogus):** Anticipate Douyin entirely removing `__pace_f` by integrating an embedded JS execution environment (`dop251/goja`) capable of solving X-Bogus encryption on the fly, similar to the original Python implementation.
- [ ] **Wails v2 Desktop GUI:** Abstract the entire `internal` directory into a Service Layer that can be imported seamlessly into Wails, eliminating the need to execute sub-shells to drive the UI.

## 3. Retrospective Opinion
The architecture pattern chosen (`Extractor` Interface containing multiple `Strategy` structs attempting parses in sequence) is an excellent implementation of the Strategy Pattern. This ensures that when Douyin invariably changes its API, only a new `Strategy` needs to be appended to the list without rewriting the pipeline.

By addressing the P0 vulnerabilities and refactoring the DVR layer into native Go (dropping FFmpeg for pure FLV dumping), the DouyinStream project will be substantially ahead of any competitor on GitHub in terms of speed, binary size, and deployment simplicity.
