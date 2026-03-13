# Audit Report 09: Threat Modeling & Roadmap Timeline (The "Failure Anticipation Plan")

**Date:** 2026-03-13  
**Auditor:** AntiGravity Expert Systems (Doctoral Level Research & Core Architecture)  
**Module:** System Resilience and Proactive Maintenance

## 1. Executive Summary
This document assumes the role of a "Doctor of Research" predicting the clinical decline of the `douyinstream-go` codebase over the next 12-24 months. ByteDance deploys massive resources into anti-scraping countermeasures. By projecting the "Timeline of Anticipated Failures," we can establish a safe, premeditated plan to refactor the architecture, ensuring the tool remains resilient (or at least degrades gracefully instead of crashing entirely).

## 2. Timeline of Anticipated Failures (The "What Will Break" Roadmap)

### Q2 2026: The CAPTCHA Wall (Probability: 95%)
**Event:** Douyin begins rolling out strict JS challenges (`TTGCaptcha`) before returning any HTML payload containing `__pace_f`.
**The Failure:** `httpclient.Get()` requests currently spoofing `Mozilla/5...` receive HTTP 200 responses filled with slider CAPTCHAs, rendering the entire JSON/Regex strategy useless. `extractStream()` reports errors instantly.
**The Proactive Refactor:**
- *Phase 1:* Implement `context.Context` tracking of `TTGCaptcha` triggers.
- *Phase 2:* Integrate a Headless Chrome driver (e.g., `github.com/chromedp/chromedp`).
- *Fallback Strategy:* Upon detecting the CAPTCHA string in HTML, DouyinStream launches an invisible Chrome instance, routes the request, waits for the JS challenge to resolve natively within V8, optionally pauses for user input (slider), and dumps the cookies back into `cookie.go` for the HTTP client to resume operations seamlessly.

### Q4 2026: The Death of `__pace_f` (Probability: 80%)
**Event:** To save SSR (Server-Side Rendering) bandwidth and improve security, Douyin completely stops injecting `streamStore` directly into the page source.
**The Failure:** All three current strategies (`DirectURL`, `JSONWrap`, `LegacyJSON`) return `error: no stream data found`. The URLs are now exclusively requested asynchronously via `fetch` by the browser after page load.
**The Proactive Refactor:**
- Advance to the `ApiWebcastStrategy`.
- Instead of downloading the HTML string, `Extractor` must execute a pure HTTP POST request to `https://live.douyin.com/webcast/room/info/` with the room ID.
- This mandates having the Javascript Sandbox (Goja) fully operational to evaluate ByteDance's `a_bogus` environmental fingerprinting algorithms necessary for the API signed headers.

### Q1 2027: Deep Packet Inspection & WebSocket Kicks (Probability: 50%)
**Event:** Live stream CDNs identify clients pulling 15MB/s of FLV data without simultaneous active WebSocket heartbeat connections.
**The Failure:** The `flv_pull_url` works perfectly for exactly 5 minutes, then abruptly receives HTTP 403 Forbidden or TCP RST by load balancers. The naive FLV downloader exits.
**The Proactive Refactor:**
- The native Go RingBuffer (designed in Report 08) must evolve.
- It must multiplex a dummy WebSocket connection (`wss://...`) subscribing to the room's heartbeat payload while the FLV stream is downloaded.
- Periodic keep-alive pings must be sent to mirror human tab-activity.

## 3. The Safe Refactoring Plan (Mitigation Roadmap)

### Immediate Term (Next 30 Days) -> **v2.0.0-Stable**
1. **Stabilize Current Operations:** Eliminate data races (add `sync.RWMutex`), utilize `viper` for Configuration mapping, and implement `sigint` teardowns for `ffmpeg`.
2. **Remove the Target:** Eliminate the hardcoded `odin_tt` and `__ac_nonce`. Inject legitimate local cookies via SQLite browser decryption. Do not poke the bear blindly.

### Mid Term (Next 3-6 Months) -> **v2.1.0**
1. **Ditch Externals:** Rewrite `recordCmd()` completely in Go. Read FLV streams directly from the `io.Reader` and implement aggressive TCP-drop reconnection logic. Stop relying on `ffmpeg` to handle a fragile network.
2. **Terminal UI:** Morph the static standard-output into a dynamic, updating TUI for recording stats (`charmbracelet/bubbletea`), giving immediate visibility into bitrates and reconnects.

### Long Term (12+ Months) -> **v3.0.0**
1. **Chromium Brain:** Standard HTTP clients (`net/http`) will no longer suffice against WAFs tracking TLS-Fingerprinting (JA3 hashes). Embed `tls.ClientHelloInfo` spoofing (e.g., `github.com/refraction-networking/utls`) or move extraction entirely to CDP (Chrome DevTools Protocol).
2. **X-Bogus Server:** Set up a local API (or load Goja) that purely focuses on solving the evolving CAPTCHAs and JS-VMPs.

## 4. Conclusion
The primary lesson from this predictive modeling is **Adaptability vs. Rigidity**. The `douyinstream-go` framework must anticipate that *everything* it depends on (HTML structure, API endpoints, Cookies, Socket stability) will change maliciously. 

By building the architecture around dynamic Cookie ingestion (`kooky`), real-browser TLS signatures (`utls`), and abstracting the Recorder into a self-healing Go loop instead of a fire-and-forget sub-process (`ffmpeg`), the project guarantees its supremacy across the entire Douyin scraping ecosystem.
