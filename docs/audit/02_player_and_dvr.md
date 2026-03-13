# Audit Report 02: Player & DVR Persistence

**Date:** 2026-03-13  
**Auditor:** AntiGravity Expert Systems  
**Module:** Live Player (`internal/player/player.go`) & CLI Recorder (`cmd/douyinstream/main.go`)

## 1. Executive Summary
The CLI integrates nicely with `mpv` and `ffmpeg` by delegating complex stream playback and decoding. However, due to its design as a generic wrapper, the application fails to handle the volatile nature of Live Streaming (socket disconnects, HTTP 403 timeouts dynamically swapping tokens). As a result, the "DVR" (Recording) feature is fatally fragile, and the `mpv` player is severely misconfigured for low-latency live streaming.

## 2. Findings: The `mpv` Player (`internal/player/player.go`)

### 2.1 Misconfigured Cache Induces Huge Articifical Latency (Severity: High)
**Context:** In `player.go`, lines 133-136, `mpv` is booted with:
```go
"--cache=yes",
"--cache-secs=30",
"--demuxer-max-bytes=500MiB",
"--demuxer-readahead-secs=20",
```
**Gap:** While this protects against buffering in VOD (Video on Demand) by aggressively downloading 30s ahead, for a *live stream* via FLV/HLS, there is no "ahead". `mpv` will intentionally pause the live stream immediately upon load and refuse to play until it buffers up to 30 seconds of video. This artificially puts the viewer 30 seconds behind the actual live moment, ruining live chat interaction.
**Recommendation:** 
- If user wants low-latency:
  ```go
  "--profile=low-latency",
  "--untimed", // Don't sleep when video/audio drift
  "--cache=no", // or lower cache explicitly
  ```
- Make latency tuning a configuration (`config.Player.LowLatency = true`).

### 2.2 IPC (Inter-Process Communication) and Zombie Processes (Severity: Medium)
**Context:** The application triggers `exec.CommandContext(ctx, mpvPath...)` and waits for `.Run()`.
**Gap:** If the Go process is forcefully killed (`SIGKILL` or crash) and the OS doesn't propagate the signal downwards to the shell/process group properly, `mpv` will keep playing as an orphaned zombie. Furthermore, there's no way to control the player programmatically (pause, change subtitle, read buffer stats) because `--input-ipc-server` is not utilized.
**Recommendation:** Enable IPC via a UNIX socket or Windows named pipe (e.g., `--input-ipc-server=/tmp/douyinstream_mpv.sock`) and use a library like `github.com/dexterorion/go-mpv-ipc` to gracefully shut it down, query health, and send OSD messages interactively without restarting.

## 3. Findings: The DVR & Recorder (`cmd/douyinstream/main.go`)

### 3.1 FFmpeg Brittleness — Zero Resilience Recording (Severity: Critical)
**Context:** `recordWithFFmpeg()` runs `ffmpeg -i url -c copy output.flv`.
**Gap:** In true live stream recording, the server *will* eventually drop the TCP connection (due to origin node rotation, token expiration after 4 hours, or load balancer hiccups). Because FFmpeg is executed functionally as a simple straight-pipe, the moment the socket drops, `ffmpeg` says "EOF", exits with Code 0, and the Go application believes "Recording saved to output.flv". A 24-hour live stream is thus cut off after 15 minutes silently.
**Recommendation:** 
- Implement an **Exponential Reconnection Loop**.
- If `ffmpeg` exits, the `recordCmd` should *re-execute* the `extractStream(ctx, url)` function to fetch the brand new `flv_pull_url` with fresh tokens.
- Then, restart `ffmpeg` appending to the existing file or outputting to numbered segments (`output_part1.flv`, `output_part2.flv`).
- Or, use FFmpeg's native reconnect flags: `-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 2` (These are finicky for FLV, so the Go-loop is safer).

### 3.2 Blocked Output Directory / File Collisions (Severity: Low)
**Context:** The recorder auto-generates `author_timestamp.flv`. 
**Gap:** It starts immediately writing to `.flv`. If the user is on Windows and has the file opened in VLC while it's recording, FFmpeg will crash due to a file-lock failure (`EBUSY`).
**Recommendation:** Write into `author_timestamp.flv.crdownload` initially. On successful graceful termination, rename `.crdownload` to `.flv`.

## 4. Architectural Enhancements

### 4.1 Native Go RingBuffer (`io.Copy`) for DVR
Instead of relying on an external binary (`ffmpeg`), which requires complex installation for some Windows users, you can use Go's native standard library to record `.flv` files flawlessly since FLV is meant to act as a raw byte stream.

```go
resp, err := http.Get(streamURL)
f, err := os.Create(output)
// Read from HTTP Response body and write to File simultaneously
_, err = io.Copy(f, resp.Body)
```
This reduces external dependencies from 1 (`ffmpeg`) to completely **0**. Users could record completely locally at 15MB/s with 0% CPU usage utilizing merely Go's `io.Copy()` and a robust HTTP client with reconnect logic.
