# 🎬 DouyinStream Go

> Watch Douyin (抖音) live streams at maximum quality — no account needed.

A cross-platform CLI tool that extracts live stream URLs from Douyin at the **highest available quality** (Origin/UHD/1080p60+), bypassing the web player's quality restrictions. Supports both **H264 and H265** codecs with up to **26 stream variants** per room.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Go Report Card](https://goreportcard.com/badge/github.com/JairFC/douyinstream-go)](https://goreportcard.com/report/github.com/JairFC/douyinstream-go)

## ✨ Features

- 🔓 **No account required** — Generates cookies dynamically, no Chinese phone number needed
- 📺 **All qualities** — Extracts Origin (原画), UHD (蓝光), HD, SD, LD + Audio-only
- 🎥 **H264 + H265** — Both codecs extracted with full metadata (resolution, FPS, bitrate)
- 🎛️ **Interactive quality selector** — Choose exactly which stream to play
- ⏺️ **Recording** — Save streams to file with ffmpeg (zero-overhead, no re-encoding)
- 🖥️ **mpv + ffplay** — Plays in external player with hardware acceleration
- 🌐 **Cross-platform** — Single binary for Linux, macOS, Windows
- 📦 **~10MB binary** — No runtime dependencies (Go static build)
- ⚡ **Adaptive extraction** — 3 strategies cascade for resilient parsing

## 🚀 Quick Start

```bash
# Build from source
git clone https://github.com/JairFC/douyinstream-go
cd douyinstream-go
make build

# Extract stream info
./bin/douyinstream extract https://live.douyin.com/ROOM_ID

# Play at maximum quality
./bin/douyinstream play https://live.douyin.com/ROOM_ID

# Play with interactive quality selector
./bin/douyinstream play --select https://live.douyin.com/ROOM_ID

# Record to file
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

### `play` — Watch a live stream

```bash
douyinstream play [flags] <url>

# Play at best quality (auto)
douyinstream play https://live.douyin.com/ROOM_ID

# Play specific quality
douyinstream play -q origin https://live.douyin.com/ROOM_ID
douyinstream play -q hd https://live.douyin.com/ROOM_ID

# Interactive quality picker
douyinstream play --select https://live.douyin.com/ROOM_ID

# Record while playing (mpv only)
douyinstream play -r output.mp4 https://live.douyin.com/ROOM_ID
```

### `extract` — Get stream URLs

```bash
douyinstream extract <url>

# Shows all available qualities, codecs, formats, and URLs
```

### `record` — Save stream to file

```bash
douyinstream record [flags] <url>

# Auto-generate filename
douyinstream record https://live.douyin.com/ROOM_ID
# → Author_20260313_120000.flv

# Custom output
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

DouyinStream extracts all available quality tiers:

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

## 🛠️ Building

### Requirements

- Go 1.21+
- Optional: `mpv` or `ffplay` for playback
- Optional: `ffmpeg` for recording

### From Source

```bash
# Standard build
make build

# Development build (with race detector)
make dev

# Cross-compile for all platforms
make build-all

# Create release with checksums
make release
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

## 🏗️ Architecture

```
cmd/douyinstream/main.go    → CLI entry (cobra)
internal/
├── extractor/
│   ├── extractor.go         → Multi-strategy orchestrator
│   └── strategies.go        → DirectURL + JSONWrap + LegacyJSON
├── cookie/cookie.go         → Dynamic cookie generation (msToken, ttwid)
├── player/player.go         → mpv + ffplay abstraction
├── platform/detect.go       → URL → Platform detection
└── config/config.go         → Configuration management
pkg/httpclient/client.go    → HTTP client with browser spoofing
```

### Extraction Pipeline

```
URL → Platform Detection → Short URL Resolution → Cookie Generation
  → HTTP GET (with spoofed headers) → CAPTCHA Check
  → Strategy Cascade (DirectURL → JSONWrap → LegacyJSON)
  → H264+H265 Quality Extraction → Best Quality Selection → Play/Record
```

## 🔧 How It Works

Douyin embeds **all quality stream URLs** in the HTML page inside `__pace_f` JavaScript blocks. The web player artificially restricts non-authenticated users to SD quality, but the HD/UHD/Origin URLs are accessible in the page source.

DouyinStream:
1. **Generates cookies dynamically** (`msToken`, `ttwid`) without a browser
2. **Fetches the page** with browser-like headers to avoid blocks
3. **Parses embedded JSON** from `__pace_f.push()` blocks
4. **Extracts all 26+ stream URLs** across H264/H265 × FLV/HLS × 7 quality tiers
5. **Selects the best quality** (Origin H265 FLV preferred)
6. **Plays via mpv/ffplay** or records via ffmpeg

## 📝 Credits

- [caiguanhao/dylive](https://github.com/caiguanhao/dylive) (MIT) — `__pace_f` parsing approach
- [iawia002/lux](https://github.com/iawia002/lux) (MIT) — Cookie generation patterns
- [douyinstream-pro](https://github.com/JairFC/douyinstream-pro) — Original Python implementation

## ⚖️ License

MIT License — see [LICENSE](LICENSE).

> **Disclaimer**: This tool is for educational and personal use only. It does not circumvent DRM or encryption. Stream URLs are publicly embedded in Douyin's HTML source. Please respect content creators and Douyin's Terms of Service.
