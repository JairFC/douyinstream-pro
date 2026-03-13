# Audit Report 05: Concurrency, Signals & Graceful Degradation

**Date:** 2026-03-13  
**Auditor:** AntiGravity Expert Systems  
**Module:** Process Orchestration (`cmd/douyinstream/main.go`)

## 1. Executive Summary
The CLI manages external binaries (`ffmpeg`, `mpv`) through the standard library's `os/exec.CommandContext`. While the application correctly traps OS signals (Ctrl+C) via `signal.NotifyContext()`, the propagation of this cancellation down to the child processes introduces a critical bug resulting in corrupted files.

## 2. Findings: `SIGKILL` vs `SIGINT` in `os/exec` (Severity: High)

### 2.1 Corrupted FLV / MP4 Demuxing on Exit
**Context:** In `main.go`, `recordWithFFmpeg()` executes:
```go
cmd := exec.CommandContext(ctx, ffmpegPath, args...)
// ...
if err := cmd.Run(); err != nil {
	if ctx.Err() != nil {
		return nil // Context cancelled (Ctrl+C)
	}
}
```
**Gap:** By default, in Go, when the `Context` passed to `CommandContext` is canceled, the `os/exec` package unconditionally sends a `SIGKILL` (or calls `Process.Kill()`) to the child process.
- **FFmpeg requires a graceful shutdown (`SIGINT` or `SIGTERM` or pressing 'q')** to correctly write the MOOV atom (for MP4) or file trailers (for FLV/MKV) and flush its I/O buffers.
- Since `CommandContext` slaughters the process instantly, any recording stopped by the user via Ctrl+C runs a very high risk of generating a corrupt, unplayable media file.

**Recommendation:** 
Do not use `CommandContext` directly for the FFmpeg recording loop if you care about the file cleanly closing. Instead:
1. Use a standard `exec.Command`.
2. Start the process with `cmd.Start()`.
3. Spin up a goroutine that waits on `<-ctx.Done()`.
4. When `ctx.Done()` triggers, send an explicit `SIGINT` (Interrupt) to `cmd.Process.Signal(os.Interrupt)` to allow FFmpeg to finish its write queues.
5. Setup a timeout (e.g., 5 seconds) after sending `SIGINT`. If the process hasn't exited cleanly by then, *then* execute `cmd.Process.Kill()`.

### 2.2 Unbounded Context in `extractStream` Phase (Severity: Low to Medium)
**Context:** The context passed to `extractStream(ctx, url)` is infinite, tied only to the lifecycle of the user not hitting Ctrl+C.
**Gap:** `http.Client.Get()` respects the `http.Client.Timeout`, but if there are logic hangs in ChromeDP (when you implement Captcha resolution), the `Extract()` phase might block the main goroutine indefinitely.
**Recommendation:** Always wrap `extractStream` in a child context with a hard timeout (e.g., 30 Seconds) specifically for the "Discovery" phase, leaving the unbounded Context strictly for the "Playback/Recording" phase.
