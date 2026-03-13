# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Browser cookie extraction (Chrome, Edge, Firefox)
- CAPTCHA handling via chromedp
- X-Bogus API signing via goja JS runtime
- Unit test suite with HTML snapshots
- DVR ring buffer recording
- Wails v2 desktop GUI

## [2.0.0-beta.1] - 2026-03-13

### Added
- **Complete Go rewrite** from Python (2,265 LOC → single binary)
- Multi-strategy extraction engine (DirectURL, JSONWrap, LegacyJSON)
- H264 + H265 dual-codec support (26 stream variants per room)
- Dynamic cookie generation (msToken, ttwid) — no account needed
- Quality tiers: Origin (原画), UHD (蓝光), HD (超清), SD, LD, MD, Audio-only
- Quality metadata extraction (resolution, FPS, bitrate, codec per stream)
- Interactive quality selector (`--select` / `-s`)
- `play` command — watch via mpv or ffplay with hardware decoding
- `extract` command — display all stream URLs and metadata
- `record` command — save to file via ffmpeg (zero re-encoding)
- Cross-platform builds (Linux, macOS, Windows × amd64/arm64)
- Makefile with build, test, lint, cross-compile, release targets
- Adaptive strategy caching (remembers last working strategy)
- Offline stream detection with graceful messaging

### Changed
- Rewritten from Python to Go for 10x smaller binary and zero runtime deps
- mpv replaces VLC as primary player (better HW decoding, IPC, 120fps+)

### Technical
- Single external dependency: `spf13/cobra` (CLI framework)
- Binary size: 6.1–6.8MB (vs Python + deps: ~50MB+)
- Go module: `github.com/JairFC/douyinstream-go`

[Unreleased]: https://github.com/JairFC/douyinstream-pro/compare/v2.0.0-beta.1...v2-go
[2.0.0-beta.1]: https://github.com/JairFC/douyinstream-pro/releases/tag/v2.0.0-beta.1
