# Audit Report 17: Architectural Protocol - Multi-CDN Dynamic Switching

**Date:** 2026-03-13  
**Auditor:** AntiGravity Expert Systems (Doctoral Level Research & Core Architecture)  
**Module:** `internal/dvr` (Advanced Resilience)

## 1. Executive Summary
Douyin distributes its massive live stream traffic across a globally distributed, hybrid Multi-CDN network (including domains like `douyincdn.com`, `douyinvod.com`, `amemv.com`). The current codebase rigidly extracts exactly one `.flv` URL and attempts to download from it until the socket dies. This is "Single Point of Failure" architecture. To achieve 99.999% uptime for 24/7 archiving, DouyinStream must implement Dynamic CDN Switching.

## 2. The Multi-CDN Degradation Problem
When a user begins recording a Douyin stream, the `Extractor` returns an `flv_pull_url` pointing to a specific CDN edge node (e.g., `pull-flv-l1`). 

**The Failure Scenario:** 
After 3 hours of recording, that specific edge node experiences severe congestion or goes offline for maintenance. The download speed drops from 5000kbps to 20kbps. The stream stutters, and the TCP socket eventually sends a `RST` packet. The naive `ffmpeg` approach simply truncates the video.

## 3. The "Active Quality-of-Experience (QoE)" Switcher Solution
We must expand the `StreamResult.Qualities` map to capture all available CDN permutations, not just resolutions. Douyin's API often provides multiple `CdnNode` objects for the same 1080p stream.

### 3.1 The Bandwidth Watchdog
Instead of a blind `io.Copy`, the Go native DVR (proposed in Report 11) must use a custom `io.Reader` wrapper that tracks byte throughput over time.
```go
type BandwidthReader struct {
    Underlying io.Reader
    BytesRead  int64
    LastTick   time.Time
    // ...
}

func (b *BandwidthReader) Read(p []byte) (n int, err error) {
    n, err = b.Underlying.Read(p)
    // Send metric to a monitoring channel
    b.trackerChan <- int64(n) 
    return n, err
}
```

### 3.2 Dynamic Seamless Switching
A background Goroutine monitors the `trackerChan`. If the rolling average bandwidth drops below the required bitrate for the current quality (e.g., drops below 800kbps for a 1080p stream) for more than 5 seconds:
1. The Watchdog intentionally closes the `io.Reader`.
2. The main DVR loop catches the custom "Bandwidth Starvation Error".
3. The DVR re-queries the `Extractor`, but this time intentionally sorts and selects a **different CDN Domain** (e.g., switching from `pull-f2` to `pull-l1`).
4. It connects to the new CDN, discards the 9-byte FLV header of the new stream, and resumes writing to the exact same file.

## 4. Benefit
You have effectively built a commercial-grade Video Player Buffer Manager inside a CLI recording tool. 
- The resulting `.flv` file on disk contains a perfectly seamless broadcast.
- The user's recording bypasses regional network outages automatically.
- Douyin's load balancers cannot successfully rate-limit the tool because it behaves exactly like the official ByteDance iOS application, rapidly switching edge-nodes when congestion is detected.
