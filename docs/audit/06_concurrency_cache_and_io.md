# Audit Report 06: Data Races, Concurrency & I/O Blocks

**Date:** 2026-03-13  
**Auditor:** AntiGravity Expert Systems  
**Module:** Core Extractor (`internal/extractor`) & Interactive Shell (`cmd/douyinstream/main.go`)

## 1. Executive Summary
While the CLI is currently sequential, the underlying architecture (`Extractor`) seems designed to be a reusable library. Unfortunately, it contains hidden data races that will induce fatal panics if ported to an asynchronous GUI (like Wails) or if multiple CLI instances are spawned globally. Additionally, there are severe I/O blocking behaviors in the interactive prompts that ignore cancellation signals.

## 2. Findings: Fatal Map Races (Severity: High)

### 2.1 Unsafe Map Mutations in `Extractor`
**Context:** In `internal/extractor/extractor.go`, `Extractor` maintains a `stats` map.
```go
func (e *Extractor) recordSuccess(name string) {
	if s, ok := e.stats[name]; ok {
		s.Successes++
	}
}
```
**Gap:** Go maps are **not safe for concurrent use**. If the `Extractor` library is ever executed by two goroutines simultaneously (e.g., extracting two stream URLs to check multiple rooms in Wails, or a CLI batch command), `recordSuccess` and `recordFailure` will trigger a concurrent map write panic, crashing the entire application immediately.
**Recommendation:** 
- Wrap `stats` with a `sync.RWMutex`.
- Or, use `sync.Map` if the map cardinality is dynamic (though a standard map + Mutex is faster here since Strategy keys are static).

## 3. Findings: Race Conditions in File I/O (Severity: Medium)

### 3.1 Unsafe `strategy_cache.json` Writes
**Context:** In `extractor.go`, `saveCache()` writes directly to the disk without any locking:
```go
_ = os.WriteFile(path, data, 0644)
```
**Gap:** 
1. **Concurrent File Corruption:** If two instances of `douyinstream extract` run simultaneously, they will race to write to `~/.cache/douyinstream/.strategy_cache.json`. This will corrupt the JSON.
2. **Error Shadowing:** The `_ = os.WriteFile` explicitly swallows all errors. If the disk is full or permissions are lost, the app fails to save cache silently.
**Recommendation:** Implement an exclusive file lock (`flock`) across the OS, or at least write to a temporary file and do an atomic `os.Rename()` to prevent corrupted JSON parsing on the next run.

## 4. Findings: Process Signal Ignorance (Severity: Medium)

### 4.1 Blocking Context in `selectQualityInteractive`
**Context:** In `main.go`, `selectQualityInteractive()` triggers:
```go
	scanner := bufio.NewScanner(os.Stdin)
	if !scanner.Scan() { ... }
```
**Gap:** This completely ignores the `Context` spawned with `signal.NotifyContext()`. If the user is at the `Enter number [1-12]: ` prompt and presses `Ctrl+C`, the application *may* not exit cleanly because `os.Stdin.Read()` is a blocking syscall that does not automatically respect Go contexts. 
**Recommendation:** Run the `scanner.Scan()` loop inside a dedicated goroutine that communicates over a channel, and `select` between the `scannerChan` and `ctx.Done()`, issuing a hard `os.Exit(0)` if `ctx.Done()` triggers during the prompt.

### 4.2 Hardcoded Fallback Leak
**Context:** In `main.go`, `extractStream()` logic:
```go
	cookies, err := cookie.GenerateDynamic(ctx)
	if err != nil {
		cookies = &cookie.Cookies{ AcNonce: "064caded4009deafd8b89" }
	}
```
**Gap:** If cookie generation eventually fails due to a network timeout, it defaults back to the exact static string that is flagged as a massive WAF vulnerability.
**Recommendation:** If dynamic generation fails, the application should *fail fast* and return an error rather than injecting a statically known "bad actor" fingerprint.
