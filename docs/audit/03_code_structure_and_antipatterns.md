# Audit Report 03: Code Structure & Patterns

**Date:** 2026-03-13  
**Auditor:** AntiGravity Expert Systems  
**Module:** Overall Codebase (Global Context)

## 1. Executive Summary
The transition from Python 3 (DouyinStream Pro v1) to Go 1.25 is remarkably well-executed locally, but retains a pseudo-scripting paradigm that doesn't fully leverage Go's strictly typed architecture. Specifically, global package-level mutations and unutilized dependency injection make the project significantly harder to test generically without standing up a live Douyin emulator.

## 2. Findings: Incomplete Data Modeling (`internal/config`)

### 2.1 The "Ghost Config" Anti-Pattern (Severity: High)
**Context:** `internal/config/config.go`
**Gap:** A deeply nested object containing structs, xdg config routing (`ConfigDir`, `CacheDir`), and sensible defaults was written. However, **not a single module consumes it**.
- The `PlayerConfig` does not set mpv’s preferred arguments.
- The `NetworkConfig.TimeoutSec` defaults to 15, but `main` hardcodes `30 * time.Second`.
- The `CookieConfig` defines "source" natively, but cookies are unconditionally grabbed via `GenerateDynamic()`.
**Impact:** It provides false confidence to a maintainer assuming a TOML file can modify the software behavior. 
**Recommendation:** Implement the standard `viper` unmarshalling, or explicitly prune the unused structures until the roadmap is ready for them. The structs must be explicitly passed into `extractor.New(cfg)` and `httpclient.New(cfg)`.

## 3. Findings: Go Standard Idioms & Scalability

### 3.1 Global `flag` Variables & Un-Testable Commands (Severity: Medium)
**Context:** `cmd/douyinstream/main.go`, lines 39-45.
```go
var (
	flagQuality string
    // ...
)
```
**Gap:** Since Cobra's commands inherently rely on mutating global package-level variables rather than bound struct references, writing unit tests for `playCmd()` or `extractCmd()` means they cannot securely run in parallel (`t.Parallel()`). If one test runs `douyinstream extract` and another runs `douyinstream play`, the globally bound flags induce race conditions.
**Recommendation:** 
```go
type extractOptions struct {
    Quality string
    Player  string
    Select  bool
}

func newExtractCmd() *cobra.Command {
    opts := &extractOptions{}
    cmd := &cobra.Command{ /* ... */ }
    cmd.Flags().StringVar(&opts.Quality, "q", "uhd", "Quality")
    return cmd
}
```

### 3.2 Improper Error Context / Silent Panics (Severity: Low)
**Context:** `internal/extractor/strategies.go` lines 242-246
In `parsePaceData()`: 
```go
		if err := json.Unmarshal([]byte(`"`+rawJSON+`"`), &unescaped); err != nil {
			continue
		}
```
**Gap:** Silent failures. While this acts as a pseudo `catch` block for invalid JSON segments, it completely obfuscates *why* Douyin's JSON failed to parse. If Douyin starts encrypting the payload differently or altering escaping rules, the application will simply report "all strategies failed", costing developers hours of debugging.
**Recommendation:** Log via `slog.Debug("failed to parse JSON segment", "err", err)` instead of silently continuing.

## 4. Architectural Enhancements

### 4.1 Interface Segregation for "Quality Tiers"
Currently, qualities are sorted inside `StreamResult.SortedQualities()` inline, doing manual $O(n^2)$ partial string searches against a list of hardcoded strings:
```go
{"origin", "原画 Origin", 0},
{"FULL_HD", "蓝光 UHD", 1},
```
**Enhancement:** Extract the Quality Ranking logic out of the data struct into a standalone `QualityRanker` interface. This allows testing quality mappings thoroughly in a `TestQualityRanking_H265_Priority` suite using pure unit test methodologies without requiring live Douyin JSON drops.

### 4.2 Separation of Concerns (`httpclient.go` -> `DouyinClient`)
`httpclient.go` currently mixes standard HTTP duties (Cookies, Headers, Redirects) with deeply tied platform logic (`ResolveShortURL`, spoofing `DefaultUserAgent`).
**Enhancement:** Abstract a `DouyinClient` that embeds or wraps `*http.Client` uniquely, passing contexts and keeping standard tools (retry logic) purely generic. This establishes a "clean architecture".
