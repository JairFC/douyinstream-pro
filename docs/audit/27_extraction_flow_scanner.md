# Audit Report 27: The Extraction Scanner Engine (State & Flow Documentation)

**Date:** 2026-03-13  
**Auditor:** AntiGravity Expert Systems (Doctoral Level Research & Core Architecture)  
**Module:** `internal/extractor` (Core Logic)

## 1. Executive Summary
Before we can rewrite `douyinstream-go` into a distributed OSINT cluster, we must completely map and standardize the "Scanner Engine" (The component that ingests a raw Douyin URL and outputs a physical playable video stream). The current codebase uses a mix of Regex, unstructured JSON mapping, and iterative fallbacks (`DirectURL`, `JSONWrap`, `LegacyJSON`). 

This document formally defines the **Ideal Universal Extraction Flow** that the V2.x rewrite must implement to guarantee 99.9% resolution success against ByteDance's modern WAFs.

## 2. The Universal Extraction Flow (The "Scanner" Pipeline)

### Phase 1: Ingestion & Normalization
1. **Input Reception:** The CLI, Web API, or Cluster Coordinator submits a raw string:
   * e.g., `https://live.douyin.com/712398402` or a mobile shortlink `https://v.douyin.com/kSjf/`
2. **Shortlink Resolution:** The engine launches an HTTP `HEAD` request (following redirects) to unwrap any `v.douyin.com` URL into its canonical `live.douyin.com/{web_rid}` format.
3. **Room ID Extraction:** A standardized RegEx `live\.douyin\.com/([A-Za-z0-9_-]+)` isolates the `{web_rid}` (Web Room ID).

### Phase 2: Stealth Initialization (Pre-Flight)
1. **Cookie Vault Checkout:** The engine connects to the `memguard` enclave (Report 25) and requests a universally valid session (`ttwid`, `__ac_nonce`). If empty, it relies on Local Kooky Extraction (Report 12).
2. **TLS Disguise:** The internal HTTP Client (`http.Client`) configures `uTLS` (Report 13) to explicitly mimic Google Chrome 118's TLS ClientHello fingerprint.
3. **Query Construction:** The URL must be built matching a native browser precisely:
   `https://live.douyin.com/{web_rid}` with Headers:
   - `User-Agent`: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...`
   - `Accept-Language`: `zh-CN,zh;q=0.9,en;q=0.8` (Crucial for passing regional WAF scoring).

### Phase 3: The Assault (Payload Extraction)
The Engine makes the `GET` request and receives the raw HTML string payload.
* **Checkpoint A (The CAPTCHA Wall):** If the response contains `captcha_verify` or returns HTTP 403, the engine instantly triggers the "Headless Fallback Protocol" (using `go-rod`, Report 16) to solve the invisible slider and regenerate the Cookie Vault.

* **Checkpoint B (The JSON Data Lake):** The engine executes a highly optimized AST/Regex parser seeking the `<script id="RENDER_DATA" type="application/json">` block. Douyin stores the entire React.js State (including the `roomStore`) encoded inside a URI-encoded string here.

### Phase 4: Data Parsing & Mapping (The Strategy Waterfall)
The engine un-escapes the JSON blob and traverses the map structure. It must dynamically test multiple access paths (Strategies) because ByteDance changes their JSON schema bi-weekly:
1. **The Modern Target:** `data.app.initialState.roomStore.roomInfo.room.stream_url.live_core_sdk_data.pull_data.stream_data`
   - Unpack this final string (which is *another* nested JSON blob) into `RawStreamData`.
2. **The Stream Dictionary:** Ensure `RawStreamData.data` contains multiple `Resolution` objects (e.g., `origin` (4K/1080p), `uhd`, `hd`, `sd`).
3. **The Multi-CDN Splitting:** Iterate through each resolution's `main` URL (The FLV) and its `hls_pull_url_map` (M3U8).

### Phase 5: Verification & Handoff
1. **The Handshake Test:** The engine opens a 500ms `TCP SYN` socket to the extracted `flv-pull` CDN node (Report 17). If the node responds, the URL is marked as `Active`.
2. **Result Compilation:** The Engine constructs the final `StreamResult` object containing Title, Streamer Name, Status (Online/Offline), and the verified slice of CDNs.
3. **Handoff:** The Pipeline hands the `StreamResult` over to the native Go-DVR (Report 11), WebRTC (Report 21), or returns it as a JSON API payload to the Cluster Coordinator.

## 3. Vulnerability Map of the Current V2.0 Scanner
The current implementation in `internal/extractor/extractor.go` fails this ideal flow in three places:
- It uses static `net/http` (Vulnerable to TLS fingerprinting).
- It brute-forces three distinct JSON paths (`DirectURL`, `JSONWrap`) which wastes CPU cycles parsing the same 2MB HTML block three times instead of parsing the JSON tree once and querying it natively.
- It lacks the "Handshake Test," frequently handing dead/congested CDNs to the player.

## 4. The Unified Refactor Plan
The V2 Scanner must be rewritten using `github.com/tidwall/gjson`. Instead of unmarshaling 2MB of Douyin HTML into standard Go Structs (which triggers massive GC lag, Report 18), `gjson` allows us to instantly pluck the `.flv` URL directly from the raw string buffer in microseconds without allocating intermediate structs in RAM.
