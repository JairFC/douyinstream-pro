# Audit Report 14: Next-Gen Feature - WebSocket Danmaku (Live Chat) Extraction

**Date:** 2026-03-13  
**Auditor:** AntiGravity Expert Systems (Doctoral Level Research & Core Architecture)  
**Module:** `internal/danmaku` (Proposed New Subsystem)

## 1. Executive Summary
A pure video recording tool represents only 50% of the live streaming ecosystem. The true value for data miners, content creators, and archivists lies in the interactive data: the live chat, gifts, and audience metrics (Danmaku). This report outlines the architecture to capture Douyin's WebSocket stream in parallel with the FLV video stream.

## 2. Technical Challenge: The Protobuf Barrier
Unlike older streaming services that use plain-text IRC or simple JSON over WebSockets, Douyin broadcasts live interactions through secure WebSockets (`wss://webcast3-ws-web-lf.douyin.com`) serialized via **Protocol Buffers (Protobuf)**.
- **Why Protobuf?** It minimizes byte footprint, allowing millions of concurrent chat messages across the platform without choking bandwidth.
- **The Difficulty:** Protobuf is a binary format. Without the exact `.proto` schema definitions, the payload is an unreadable stream of bytes. Furthermore, the WebSocket connection requires periodic "heartbeats" (Ping/Pong frames) to keep the connection alive.

## 3. The Go-Native Architecture Solution

### 3.1 Reverse Engineering the `.proto` Files
Recent open-source breakthroughs (e.g., `zboyco/douyin-live-go`) have successfully mapped Douyin's Protobuf definitions. We must import or transpile these schemas into our project.

The architecture will require generating Go structs using `protoc`:
```protobuf
// Example reversed proto structure
message ChatMessage {
    User user = 1;
    string content = 2;
    // ...
}
message GiftMessage {
    int64 gift_id = 1;
    int32 count = 2;
    // ...
}
```

### 3.2 The WebSocket Daemon
We will introduce `github.com/gorilla/websocket` into the project.

**Architecture Flow:**
1. During `extractStream()`, alongside scraping the `flv_pull_url`, we extract the `wss://` URI and the internal `room_id`.
2. A dedicated goroutine initializes `gorilla/websocket` and connects to the WSS endpoint.
3. **The Heartbeat:** A `time.Ticker` will send an empty Protobuf payload (`PingMessage`) every 10 seconds to satisfy the WAF.
4. **The Listener:** A `for {}` loop reads incoming binary messages, uses `proto.Unmarshal` to deserialize them into Go structs, and routes them to a Go Channel.

### 3.3 The Output Pipeline
The CLI will accept a flag `--record-chat`. When enabled, the routed messages are formatted and written synchronously:
- **`.srt` (SubRip):** Time-stamped subtitle file synchronized with the FLV recording length. When the user plays `.flv` in VLC, the Douyin chat crawls naturally across the bottom of the screen.
- **`.jsonl` (JSON-Lines):** A raw data dump for machine learning and sentiment analysis.

## 4. Strategic Impact
Adding Danmaku extraction elevates `douyinstream-go` from a "downloader" to a "Live Analytics Engine". It allows developers to build bots that trigger events based on gifts, or archivists to preserve the entire cultural context of a broadcast, not just the pixels.
