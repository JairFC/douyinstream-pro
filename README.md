# 🎬 DouyinStream Go

**English** | [中文文档](README_CN.md)

> Watch, extract, and record Douyin (抖音) live streams at maximum quality — no account needed.

A cross-platform CLI tool written in **pure Go** that extracts live stream URLs from Douyin at the **highest available quality** (Origin/UHD/1080p60+), bypassing the web player's quality restrictions. Supports both **H264 and H265** codecs with up to **26 stream variants** per room.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Go Report Card](https://goreportcard.com/badge/github.com/JairFC/douyinstream-go)](https://goreportcard.com/report/github.com/JairFC/douyinstream-go)
[![CI](https://github.com/JairFC/douyinstream-go/actions/workflows/ci.yml/badge.svg?branch=v2-go)](https://github.com/JairFC/douyinstream-go/actions/workflows/ci.yml)

> **Current Version:** `v2.0.0-beta.2` — Complete Go rewrite. Stable core extraction, playback, and recording. Undergoing military-grade audit (28 reports). See [Roadmap](#-roadmap).

---

## ✨ Features

| Feature | Status | Details |
|---------|--------|---------|
| 🔓 No account required | ✅ Stable | Dynamic cookie generation (`msToken`, `ttwid`) |
| 📺 All quality tiers | ✅ Stable | Origin (原画), UHD (蓝光), HD, SD, LD + Audio-only |
| 🎥 H264 + H265 codecs | ✅ Stable | Both codecs with full metadata (resolution, FPS, bitrate) |
| 🎛️ Interactive quality selector | ✅ Stable | Choose any of the 26+ stream variants |
| ⏺️ Recording via FFmpeg | ✅ Stable | Zero-overhead copy (`-c copy`), no re-encoding |
| 🖥️ mpv + ffplay playback | ✅ Stable | Hardware-accelerated external player |
| ⚡ 3-strategy extraction | ✅ Stable | DirectURL → JSONWrap → LegacyJSON cascade |
| 🌐 Cross-platform | ✅ Stable | Single static binary for Linux, macOS, Windows |
| 📦 Lightweight binary | ✅ Stable | ~10MB, zero runtime dependencies |
| 🔄 Strategy caching | ✅ Stable | Remembers last successful extraction strategy |

## 🚀 Quick Start

```bash
# Clone and build
git clone https://github.com/JairFC/douyinstream-go
cd douyinstream-go
make build

# Extract stream info (shows all qualities and URLs)
./bin/douyinstream extract https://live.douyin.com/ROOM_ID

# Play at maximum quality (auto-selects best)
./bin/douyinstream play https://live.douyin.com/ROOM_ID

# Play with interactive quality picker
./bin/douyinstream play --select https://live.douyin.com/ROOM_ID

# Record stream to file (auto-generates filename)
./bin/douyinstream record https://live.douyin.com/ROOM_ID
```

## 📺 Example Output

```
$ douyinstream extract https://live.douyin.com/754155033397

📡 Stream: 永劫无间连招考核，全面解析，新手也能看得懂。
👤 Author: 音择（永劫无间）
🔴 Live:   true
🆔 Room:   7616791517541550848

📺 Available qualities:
   1. 🟣 原画 Origin (FLV H265)  14778kbps 60fps
   2. 🟣 原画 Origin (FLV H264)  14778kbps 60fps
   3. 🔵 蓝光 UHD (FLV H265)     7600kbps 60fps
   4. 🔵 蓝光 UHD (FLV H264)     8000kbps 60fps
   5. 🟡 超清 HD (FLV H265)      4200kbps 60fps
   6. 🟡 超清 HD (FLV H264)      6000kbps 60fps
   7. 🟠 SD (FLV H265)           2400kbps 60fps
   ... (+ HLS variants, Audio-only)

🏆 Best URL:
  http://pull-flv-...douyincdn.com/.../stream-..._uhd.flv?...
```

## 🎮 Commands

### `extract` — Get stream URLs

```bash
douyinstream extract <url>
# Shows all available qualities, codecs, formats, and direct URLs
```

### `play` — Watch a live stream

```bash
# Play at best quality (auto)
douyinstream play https://live.douyin.com/ROOM_ID

# Play specific quality tier
douyinstream play -q origin https://live.douyin.com/ROOM_ID

# Interactive quality picker
douyinstream play --select https://live.douyin.com/ROOM_ID

# Record while playing (mpv only)
douyinstream play -r output.mp4 https://live.douyin.com/ROOM_ID
```

### `record` — Save stream to file

```bash
# Auto-generate filename: Author_20260313_120000.flv
douyinstream record https://live.douyin.com/ROOM_ID

# Custom output path
douyinstream record -o stream.mp4 https://live.douyin.com/ROOM_ID

# Record at specific quality
douyinstream record -q origin -o best.flv https://live.douyin.com/ROOM_ID
```

### Global Flags

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--quality` | `-q` | `uhd` | Quality: `origin`, `uhd`, `hd`, `sd`, `ld` |
| `--select` | `-s` | `false` | Interactive quality picker |
| `--player` | `-p` | auto | Player: `mpv`, `ffplay` |
| `--record` | `-r` | - | Record stream while playing |
| `--verbose` | `-v` | `false` | Debug logging |

## 📐 Quality Tiers

DouyinStream extracts all available quality tiers from Douyin's embedded stream data:

| Tier | Chinese | Description | Typical Specs |
|------|---------|-------------|---------------|
| 🟣 Origin | 原画 | Streamer's original quality | Up to 4K 120fps |
| 🔵 UHD | 蓝光 | Blu-ray quality | 1920×1080 60fps |
| 🟡 HD | 超清 | Ultra-clear | 1280×720 60fps |
| 🟠 SD | 高清 | High-clear | 1280×720 30fps |
| 🔴 LD | 标清 | Standard | 960×540 25fps |
| 🔴 MD | 流畅 | Smooth | Low bitrate 15fps |
| ⚫ AO | - | Audio only | Audio stream |

Each tier is available in **H264** and **H265** codecs, as both **FLV** and **HLS** formats.

## 🏗️ Architecture

```
douyinstream-go/
├── cmd/douyinstream/
│   └── main.go              → CLI entrypoint (Cobra commands, signal handling)
├── internal/
│   ├── extractor/
│   │   ├── extractor.go     → Multi-strategy orchestrator (Extract → StreamResult)
│   │   └── strategies.go    → DirectURL + JSONWrap + LegacyJSON parsers
│   ├── cookie/cookie.go     → Dynamic cookie generation (msToken, ttwid)
│   ├── player/player.go     → mpv + ffplay abstraction layer
│   ├── platform/detect.go   → URL → Platform detection & routing
│   └── config/config.go     → Configuration management (TOML, planned)
├── pkg/httpclient/client.go → HTTP client with browser header spoofing
├── docs/audit/              → 28 military-grade audit reports (see below)
├── Makefile                 → Build, test, lint, cross-compile, release
└── .github/workflows/ci.yml → CI pipeline (build, test, lint, cross-compile)
```

### Extraction Pipeline

```
Input URL
  │
  ├─ Short URL? ──→ HTTP HEAD redirect resolution
  │
  ▼
Platform Detection (live.douyin.com)
  │
  ▼
Cookie Generation (msToken + ttwid — no browser needed)
  │
  ▼
HTTP GET with spoofed headers (User-Agent, Referer, Accept-Language)
  │
  ├─ CAPTCHA detected? ──→ Abort with warning (headless fallback planned)
  │
  ▼
Strategy Cascade (tries each until one succeeds):
  ├─ 1. DirectURL  → Parses stream data from <script id="RENDER_DATA">
  ├─ 2. JSONWrap   → Parses nested JSON inside __pace_f.push() blocks
  └─ 3. LegacyJSON → Falls back to older JSON extraction patterns
  │
  ▼
StreamResult (Title, Author, Status, Qualities[])
  │
  ▼
Quality Selection (auto-best / --select interactive / -q flag)
  │
  ▼
Output: Play (mpv/ffplay) │ Record (ffmpeg -c copy) │ Print URLs
```

## 🛠️ Building

### Requirements

- **Go 1.21+** (developed on Go 1.25)
- **Optional:** `mpv` or `ffplay` for playback
- **Optional:** `ffmpeg` for recording

### From Source

```bash
make build          # Build for current platform
make dev            # Build with race detector (development)
make build-all      # Cross-compile for all 5 platforms
make release        # Build release artifacts + SHA256 checksums
make test           # Run all tests
make lint           # Run go vet + staticcheck
```

### Pre-built Binaries

Download from [Releases](https://github.com/JairFC/douyinstream-go/releases).

| Platform | Binary |
|----------|--------|
| Linux x64 | `douyinstream-linux-amd64` |
| Linux ARM64 | `douyinstream-linux-arm64` |
| macOS Intel | `douyinstream-darwin-amd64` |
| macOS Apple Silicon | `douyinstream-darwin-arm64` |
| Windows x64 | `douyinstream-windows-amd64.exe` |

## 🔧 How It Works

Douyin embeds **all quality stream URLs** in the HTML page inside `__pace_f` JavaScript blocks and `<script id="RENDER_DATA">` tags. The web player artificially restricts non-authenticated users to SD quality, but the HD/UHD/Origin URLs are accessible in the page source.

DouyinStream:
1. **Generates cookies dynamically** (`msToken`, `ttwid`) without launching a browser
2. **Fetches the page** with browser-like headers to avoid WAF blocks
3. **Parses embedded JSON** using a 3-strategy cascade for resilience
4. **Extracts all 26+ stream URLs** across H264/H265 × FLV/HLS × 7 quality tiers
5. **Selects the best quality** (Origin H265 FLV preferred)
6. **Plays via mpv/ffplay** or records via ffmpeg (`-c copy`, zero re-encoding)

## 🔬 Audit Reports

A comprehensive military-grade audit has been performed on the entire codebase, covering security, architecture, performance, and future expansion strategies. **28 detailed reports** are available in [`docs/audit/`](docs/audit/).

See the full categorized index: **[`docs/audit/00_MASTER_INDEX.md`](docs/audit/00_MASTER_INDEX.md)**

Summary of categories:
- **Phase 1:** Critical bugs, data races, and code smells (6 reports)
- **Phase 2:** Military-grade security — supply chain, forensics, DNS (6 reports)
- **Phase 3:** Core extraction engine and anti-WAF evasion (6 reports)
- **Phase 4:** High-performance engine — zero-copy I/O, GC tuning (6 reports)
- **Phase 5:** Modern expansions — WebRTC, AI inference, cloud-native (4 reports)

## 🗺️ Roadmap

### ✅ v2.0.0-beta.2 (Current — March 2026)
- [x] Full Go rewrite from Python (`douyinstream-pro`)
- [x] 3-strategy extraction engine (DirectURL, JSONWrap, LegacyJSON)
- [x] Dynamic cookie generation (no browser dependency)
- [x] H264 + H265 dual-codec extraction with FLV + HLS formats
- [x] Interactive quality selector with 26+ stream variants
- [x] Recording via FFmpeg (`-c copy`) with auto-filename
- [x] Playback via mpv + ffplay with hardware acceleration
- [x] Cross-platform builds (Linux, macOS, Windows × amd64/arm64)
- [x] CI pipeline (GitHub Actions: build, test, lint, cross-compile)
- [x] Makefile with release automation and SHA256 checksums
- [x] Strategy caching (remembers last successful approach)
- [x] Military-grade audit (28 reports, categorized index)

### 🔜 v2.1.0 (Planned — Stability & Hardening)
- [ ] Fix data races in map mutations (`sync.RWMutex`)
- [ ] Graceful shutdown for FFmpeg (`SIGINT` instead of `SIGKILL`)
- [ ] Configuration system via TOML/Viper (`config.toml`)
- [ ] HTTP retry logic with exponential backoff
- [ ] Supply chain hardening (`-mod=readonly`, `govulncheck`)
- [ ] Reproducible builds (`-buildid=`, `-trimpath`)

### 🔮 v2.2.0+ (Future — Advanced Features)
- [ ] Native Go DVR engine (eliminate FFmpeg dependency for recording)
- [ ] TLS fingerprint spoofing (`uTLS` — mimic Chrome ClientHello)
- [ ] Local browser cookie extraction (`kooky` library)
- [ ] TUI dashboard (`charmbracelet/bubbletea`)
- [ ] WebSocket Danmaku (live chat/gifts) capture via Protobuf
- [ ] Multi-CDN dynamic switching for 24/7 recording resilience
- [ ] GC tuning (`GOGC/GOMEMLIMIT`) for continuous operation
- [ ] Direct-to-S3 recording (Cloudflare R2 / Backblaze B2)

### 🧪 v3.0.0 (Research — Experimental)
- [ ] WebRTC extraction via Pion (next-gen low-latency protocol)
- [ ] JS-VMP signature generation (`X-Bogus`, `a_bogus` via Goja)
- [ ] Headless CDP fallback for CAPTCHA solving (`go-rod`)
- [ ] Real-time AI inference (Whisper transcription, YOLO triggers)
- [ ] eBPF TLS key extraction (Linux kernel-level stealth)
- [ ] Distributed cluster mode (Watcher + Worker swarm + S3)

## 🧰 Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Go 1.25 (static binary, zero runtime deps) |
| CLI Framework | [Cobra](https://github.com/spf13/cobra) |
| HTTP Client | `net/http` with browser header spoofing |
| Playback | `mpv`, `ffplay` (via `os/exec`) |
| Recording | `ffmpeg` (via `os/exec`, `-c copy`) |
| Build System | `Makefile` + `go build -trimpath -ldflags` |
| CI/CD | GitHub Actions (3-OS matrix + cross-compile) |
| Versioning | SemVer + Git tags (`v2.0.0-beta.2`) |

## 📝 Credits

- [caiguanhao/dylive](https://github.com/caiguanhao/dylive) (MIT) — `__pace_f` parsing approach
- [iawia002/lux](https://github.com/iawia002/lux) (MIT) — Cookie generation patterns
- [douyinstream-pro](https://github.com/JairFC/douyinstream-pro) — Original Python implementation

## ⚖️ License

MIT License — see [LICENSE](LICENSE).

> **Disclaimer**: This tool is for educational and personal use only. It does not circumvent DRM or encryption. Stream URLs are publicly embedded in Douyin's HTML source. Please respect content creators and Douyin's Terms of Service.
