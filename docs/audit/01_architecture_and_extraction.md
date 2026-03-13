# Audit Report 01: Architecture & Extraction Resilience

**Date:** 2026-03-13  
**Auditor:** AntiGravity Expert Systems  
**Module:** Core Extraction (`internal/extractor`) & Network (`pkg/httpclient`)

## 1. Executive Summary
The multi-strategy approach (DirectURL, JSONWrap, LegacyJSON) is a robust architectural pattern that isolates parsing failures. However, the implementation details within these strategies rely on fragile string slicing and vulnerable static tokens that expose the application to severe WAF (Web Application Firewall) blocking.

## 2. Findings: Core Extraction (`internal/extractor/strategies.go`)

### 2.1 Fragile `__pace_f` Parsing (Severity: High)
**Context:** `parsePaceData(html string)` extracts JSON blocks by manually searching for `"__pace_f"`, finding the next `"`, and slicing until `</script>`, then doing a manual `LastIndex` of `"`.
**Gap:** This is an $O(n)$ string manipulation approach with zero semantic understanding of the HTML. 
- If Douyin minifies the JavaScript differently (e.g., `__pace_f("... )` instead of `__pace_f("...")`).
- If Douyin uses single quotes `__pace_f('...')`.
- If there is an escaped quote inside the JSON string before the end tag.
- In all these cases, `parsePaceData` will panic or silently fail to extract the JSON.
**Recommendation:** 
Refactor `parsePaceData` to use a strict Regex with non-greedy capture groups, or better, an AST-based JavaScript tokenizer (like `github.com/dop251/goja` which is already planned for the project) to safely extract the arguments passed to `__pace_f.push()`.
**Suggested Regex:** `(?s)__pace_f\.push\(\s*\[[^,]+,\s*"({.*?})"\s*\]\s*\)` (Needs adaptation to exact Douyin payload).

### 2.2 Redundant JSON Decoding Iterations (Severity: Low)
**Context:** In `parseRoomData()`, the code iterates over arbitrary arrays attempting to unmarshal every single element into `map[string]json.RawMessage` just to check if it contains `"state"`.
**Gap:** This is CPU intensive. While Go is fast, trying to JSON decode massive state dumps blindly is inefficient.
**Recommendation:** Wrap the `json.Unmarshal` in a lightweight string check (`strings.Contains(string(element), '"state"')`) before attempting full deserialization.

### 2.3 Hardcoded `odin_tt` and `__ac_nonce` (Severity: Critical)
**Context:** `internal/cookie/cookie.go` lines 91-92.
**Gap:** `odin_tt` and `__ac_nonce` are highly targeted telemetry vectors for ByteDance's risk control system. Hardcoding them means every single user of this CLI globally shares the exact same browser footprint. If ByteDance bans this specific `odin_tt` hash, the application will break globally.
**Recommendation:** 
- The `__ac_nonce` should ideally be fetched from a pre-flight request, or dynamically scraped.
- Implement the "Browser Cookie Extraction" feature (using `github.com/kooky/kooky` or similar) as the *highest priority* task to allow users to inject their own genuine, authenticated tokens trivially.

## 3. Findings: Network Layer (`pkg/httpclient/client.go`)

### 3.1 Hardcoded User-Agent (Severity: Medium)
**Context:** `DefaultUserAgent = "Mozilla/5.0... Chrome/120.0.0.0..."`
**Gap:** Chrome 120 is already outdated. Static User-Agents act as a secondary fingerprint. 
**Recommendation:** Implement an array of modern User-Agents (Chrome 122+, Edge, Safari) and select one randomly per session, or fetch an updated list dynamically.

### 3.2 Missing Retry / Backoff Logic (Severity: Medium)
**Context:** `Extract()` and `Get()` execute a single HTTP request.
**Gap:** Douyin's servers frequently return HTTP 429 (Too Many Requests), 502, or drop connections. The CLI immediately errors out and dies.
**Recommendation:** Implement an Exponential Backoff retry mechanism inside `httpclient.Get()`. e.g., using `github.com/cenkalti/backoff/v4`. If a request fails due to network (not 404), it should retry 3 times with jitter.

## 4. Architectural Enhancements

- **Dependency Injection for Config:** The `httpclient` should accept the `NetworkConfig` (from `internal/config`) to set its Timeout and Retry limits dynamically, rather than using hardcoded constants in `client.go`.
