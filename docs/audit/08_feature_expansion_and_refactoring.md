# Audit Report 08: Feature Expansion & Architectural Refactoring

**Date:** 2026-03-13  
**Auditor:** AntiGravity Expert Systems (Doctoral Level Research & Core Architecture)  
**Module:** Next-Generation Features & State-of-the-Art Alignments

## 1. Executive Summary
Following the audit of the current v2.0.0-beta.1 codebase, this report details the necessary paradigms and features required to elevate DouyinStream from a basic HTML scraper to a robust, "bulletproof" Enterprise API Client. The research indicates that similar tools globally (`Lux`, `dylive`, `douyin-live-recorder`) are continuously battling ByteDance's JS-VMP (JavaScript Virtual Machine Protection). Our architecture must preemptively adapt.

## 2. Refactoring The Core: The "Smart DVR" Engine

### 2.1 The Native Go RingBuffer (Dropping FFmpeg Dependency)
**Current State:** Recording relies heavily on `os/exec` piping to `ffmpeg -c copy`. When the network stutters, FFmpeg exits cleanly (Code 0), and the recording truncates irreversibly.
**The Refactor:**
We must implement a native `FlvWriter` in Go. FLV (Flash Video) is an extremely simple container format consisting of a 9-byte header and continuous "tags" (Audio, Video, Meta).
- **Infinite Reconnect Logic:** Open an `http.Get(flv_url)` request. Pipe the `resp.Body` through an `io.Copy()` chunk by chunk.
- If the socket dies (`EOF` or timeout), the Go routine intercepts the error, leaves the `.flv` file descriptor open, calls the `Extractor` to get a fresh `flv_pull_url`, and resumes writing the raw FLV tags. 
- **Benefit:** 100% dependency-free binaries (no FFmpeg needed), 0 bytes lost during network reconnects, and endless 24/7 stream archiving.

### 2.2 Local Cookie Extraction (Silent Authentication)
**The Feature:** Instead of spoofing `odin_tt` and `__ac_nonce` blindly (which flags Douyin's bot-detection), the CLI should intelligently harvest authenticated sessions.
**The Refactor:**
Integrate a library like `github.com/zellyn/kooky`.
- Have a command `douyinstream config auth-browser` that scans the user's local SQLite Chrome/Edge/Firefox profiles.
- Extract `ttwid`, `passport_csrf_token`, and `sessionid` associated with `v.douyin.com`.
- Encrypt and store these in `~/.config/douyinstream/config.toml`.
- **Benefit:** Streams are now requested using a 100% legitimate, pre-warmed user session. WAF bans drop to zero.

## 3. Anticipating Douyin API Mutations (`X-Bogus` & `a_bogus`)

### 3.1 The End of `__pace_f`
**State-of-the-Art Research:** Open source projects like `TikTokDownloader` and API scrapers have documented that ByteDance is aggressively phasing out dumping `streamStore` directly inside the initial HTML HTML `<script id="RENDER_DATA">` or `__pace_f`. They are shifting to dynamically fetching the stream URL via `/webcast/room/info/`.
**The Feature:** To query the webcast API, Douyin strictly enforces JS-VMP signatures (`X-Bogus` and the newer `a_bogus`).
**The Refactor:**
- We cannot port `a_bogus` to Go natively; the obfuscation mutates too frequently.
- We must embed a V8 engine or pure Go JS interpreter. You previously imported `github.com/dop251/goja`, but it's currently unused.
- Create `internal/signer/signer.go`. It should load the raw Douyin JS challenge file, evaluate the AST using Goja, inject a mock `window/document` DOM environment, and execute `window._vmp_sign("url")` to generate the `a_bogus` string.
- When `JSONWrapStrategy` fails, the `Extractor` gracefully degrades into `ApiWebcastStrategy`, signs the request, and fetches the JSON asynchronously.

## 4. UI / UX Expansion

### 4.1 CLI Dashboard (TUI)
Instead of scrolling text, live streaming extraction warrants a TUI (Terminal User Interface).
- **Feature:** Integrate `github.com/charmbracelet/bubbletea`.
- Upon running `douyinstream record <url>`, replace the terminal with a live dashboard showing:
  - 🔴 Live Status
  - ⏱️ Uptime / Recording Duration
  - 💾 Megabytes Written (updated every 1s)
  - ⚡ Bitrate speed
  - 🔄 Reconnection attempts in real-time.

### 4.2 WebSockets Chat Extraction
The ultimate live stream tool captures both Video and Chat.
- **Feature:** Parallel to `flv_pull_url`, parse the `wss://webcast3-ws-web-lf.douyin.com` URL.
- Decode the Protobuf (Protocol Buffers) payloads to dump live chat into a `.jsonl` or `.srt` subtitle file alongside the video recording.
