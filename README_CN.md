# 🎬 DouyinStream Go

> 以最高画质观看、提取、录制抖音直播 — 无需登录账号

[English](README.md) | **中文**

纯 **Go 语言**编写的跨平台命令行工具，从抖音直播间提取最高画质的直播流（原画/蓝光/1080p60+），
绕过网页播放器的画质限制。支持 **H264 和 H265** 双编码，每个直播间可提取多达 **26 路流**。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Go Report Card](https://goreportcard.com/badge/github.com/JairFC/douyinstream-go)](https://goreportcard.com/report/github.com/JairFC/douyinstream-go)
[![CI](https://github.com/JairFC/douyinstream-go/actions/workflows/ci.yml/badge.svg?branch=v2-go)](https://github.com/JairFC/douyinstream-go/actions/workflows/ci.yml)

> **当前版本:** `v2.0.0-beta.2` — 完整的 Go 重写版本。核心提取、播放、录制功能稳定。已完成军事级代码审计（28 份报告）。参见[开发路线图](#-开发路线图)。

---

## ✨ 功能特性

| 功能 | 状态 | 说明 |
|------|------|------|
| 🔓 无需账号 | ✅ 稳定 | 动态生成 Cookie（`msToken`、`ttwid`） |
| 📺 全部画质 | ✅ 稳定 | 原画、蓝光、超清、高清、标清 + 纯音频 |
| 🎥 H264 + H265 | ✅ 稳定 | 双编码提取，含完整元数据（分辨率、帧率、码率） |
| 🎛️ 交互式画质选择 | ✅ 稳定 | 自由选择 26+ 路流中的任意一路 |
| ⏺️ FFmpeg 录制 | ✅ 稳定 | 零开销复制（`-c copy`），无需重编码 |
| 🖥️ mpv + ffplay 播放 | ✅ 稳定 | 外置播放器，支持硬件加速 |
| ⚡ 三策略提取 | ✅ 稳定 | DirectURL → JSONWrap → LegacyJSON 级联 |
| 🌐 全平台 | ✅ 稳定 | Linux、macOS、Windows 单文件静态编译 |
| 📦 轻量二进制 | ✅ 稳定 | ~10MB，零运行时依赖 |
| 🔄 策略缓存 | ✅ 稳定 | 记住上次成功的提取策略 |

## 🚀 快速开始

```bash
# 从源码编译
git clone https://github.com/JairFC/douyinstream-go
cd douyinstream-go
make build

# 提取直播流信息（显示所有画质和地址）
./bin/douyinstream extract https://live.douyin.com/直播间ID

# 以最高画质播放（自动选择最佳）
./bin/douyinstream play https://live.douyin.com/直播间ID

# 交互式选择画质
./bin/douyinstream play --select https://live.douyin.com/直播间ID

# 录制直播流（自动生成文件名）
./bin/douyinstream record https://live.douyin.com/直播间ID
```

## 📺 输出示例

```
$ douyinstream extract https://live.douyin.com/754155033397

📡 直播间: 永劫无间连招考核，全面解析，新手也能看得懂。
👤 主播: 音择（永劫无间）
🔴 状态: 直播中
🆔 房间号: 7616791517541550848

📺 可用画质:
   1. 🟣 原画 Origin (FLV H265)  14778kbps 60fps
   2. 🟣 原画 Origin (FLV H264)  14778kbps 60fps
   3. 🔵 蓝光 UHD (FLV H265)     7600kbps 60fps
   4. 🔵 蓝光 UHD (FLV H264)     8000kbps 60fps
   5. 🟡 超清 HD (FLV H265)      4200kbps 60fps
   6. 🟡 超清 HD (FLV H264)      6000kbps 60fps
   ... (+ HLS 版本，纯音频)

🏆 最佳地址:
  http://pull-flv-...douyincdn.com/.../stream-..._uhd.flv?...
```

## 🎮 命令说明

### `extract` — 获取直播流地址

```bash
douyinstream extract <url>
# 显示所有可用画质、编码、格式和直接地址
```

### `play` — 观看直播

```bash
# 自动选择最高画质
douyinstream play https://live.douyin.com/直播间ID

# 指定画质
douyinstream play -q origin https://live.douyin.com/直播间ID

# 交互式选择
douyinstream play --select https://live.douyin.com/直播间ID

# 边看边录（仅 mpv）
douyinstream play -r output.mp4 https://live.douyin.com/直播间ID
```

### `record` — 录制直播

```bash
# 自动生成文件名：主播名_20260313_120000.flv
douyinstream record https://live.douyin.com/直播间ID

# 指定输出文件
douyinstream record -o stream.mp4 https://live.douyin.com/直播间ID

# 以指定画质录制
douyinstream record -q origin -o best.flv https://live.douyin.com/直播间ID
```

### 全局参数

| 参数 | 缩写 | 默认值 | 说明 |
|------|------|--------|------|
| `--quality` | `-q` | `uhd` | 画质: `origin`, `uhd`, `hd`, `sd`, `ld` |
| `--select` | `-s` | `false` | 交互式画质选择 |
| `--player` | `-p` | 自动 | 播放器: `mpv`, `ffplay` |
| `--record` | `-r` | - | 边播边录 |
| `--verbose` | `-v` | `false` | 调试日志 |

## 📐 画质等级

| 等级 | 中文名 | 说明 | 典型规格 |
|------|--------|------|----------|
| 🟣 Origin | 原画 | 主播原始画质 | 最高 4K 120fps |
| 🔵 UHD | 蓝光 | 蓝光画质 | 1920×1080 60fps |
| 🟡 HD | 超清 | 超清画质 | 1280×720 60fps |
| 🟠 SD | 高清 | 高清画质 | 1280×720 30fps |
| 🔴 LD | 标清 | 标清画质 | 960×540 25fps |
| 🔴 MD | 流畅 | 流畅画质 | 低码率 15fps |
| ⚫ AO | - | 纯音频 | 音频流 |

每个等级提供 **H264** 和 **H265** 两种编码，以及 **FLV** 和 **HLS** 两种格式。

## 🏗️ 项目结构

```
douyinstream-go/
├── cmd/douyinstream/
│   └── main.go              → CLI 入口（Cobra 命令、信号处理）
├── internal/
│   ├── extractor/
│   │   ├── extractor.go     → 多策略编排器（Extract → StreamResult）
│   │   └── strategies.go    → DirectURL + JSONWrap + LegacyJSON 解析器
│   ├── cookie/cookie.go     → 动态 Cookie 生成（msToken、ttwid）
│   ├── player/player.go     → mpv + ffplay 抽象层
│   ├── platform/detect.go   → URL → 平台检测与路由
│   └── config/config.go     → 配置管理（TOML，计划中）
├── pkg/httpclient/client.go → HTTP 客户端（浏览器请求头伪装）
├── docs/audit/              → 28 份军事级审计报告
├── Makefile                 → 构建、测试、检查、交叉编译、发布
└── .github/workflows/ci.yml → CI 流水线（构建、测试、检查、交叉编译）
```

### 提取流程

```
输入 URL
  │
  ├─ 短链接？ ──→ HTTP HEAD 重定向解析
  │
  ▼
平台检测 (live.douyin.com)
  │
  ▼
Cookie 生成（msToken + ttwid — 无需浏览器）
  │
  ▼
HTTP GET 请求（伪装 User-Agent、Referer、Accept-Language）
  │
  ├─ 检测到验证码？ ──→ 中止并警告（无头浏览器回退计划中）
  │
  ▼
策略级联（逐一尝试，直到成功）:
  ├─ 1. DirectURL  → 从 <script id="RENDER_DATA"> 解析
  ├─ 2. JSONWrap   → 从 __pace_f.push() 块解析嵌套 JSON
  └─ 3. LegacyJSON → 回退到旧版 JSON 提取模式
  │
  ▼
StreamResult（标题、主播、状态、画质列表[]）
  │
  ▼
画质选择（自动最佳 / --select 交互 / -q 指定）
  │
  ▼
输出: 播放 (mpv/ffplay) │ 录制 (ffmpeg -c copy) │ 打印地址
```

## 🛠️ 编译安装

### 环境要求

- **Go 1.21+**（开发使用 Go 1.25）
- **可选:** `mpv` 或 `ffplay`（用于播放）
- **可选:** `ffmpeg`（用于录制）

### 从源码编译

```bash
make build          # 编译当前平台
make dev            # 带竞态检测器编译（开发模式）
make build-all      # 全平台交叉编译（5 个平台）
make release        # 构建发布包 + SHA256 校验和
make test           # 运行所有测试
make lint           # 运行 go vet + staticcheck
```

### 预编译文件

从 [Releases](https://github.com/JairFC/douyinstream-go/releases) 下载：

| 平台 | 文件 |
|------|------|
| Linux x64 | `douyinstream-linux-amd64` |
| Linux ARM64 | `douyinstream-linux-arm64` |
| macOS Intel | `douyinstream-darwin-amd64` |
| macOS Apple Silicon | `douyinstream-darwin-arm64` |
| Windows x64 | `douyinstream-windows-amd64.exe` |

## 🔧 工作原理

抖音在直播页面的 HTML 中将**所有画质的直播流地址**嵌入到 `__pace_f` JavaScript 块和 `<script id="RENDER_DATA">` 标签中。
网页播放器通过前端代码限制未登录用户只能观看标清画质，但所有画质的地址实际上已经在页面源码中。

DouyinStream 的工作流程：
1. **动态生成 Cookie**（`msToken`、`ttwid`），无需启动浏览器
2. 使用浏览器模拟的请求头**获取页面**，绕过 WAF 防护
3. 使用**三策略级联**解析嵌入的 JSON 数据
4. 提取 H264/H265 × FLV/HLS × 7 个画质等级的**全部 26+ 路流地址**
5. **选择最高画质**（优先原画 H265 FLV）
6. 通过 **mpv/ffplay 播放**或通过 **ffmpeg 录制**（`-c copy`，零重编码）

## 🔬 审计报告

已对整个代码库进行了军事级全面审计，涵盖安全性、架构、性能和未来扩展策略。**28 份详细报告**位于 [`docs/audit/`](docs/audit/)。

查看完整分类索引：**[`docs/audit/00_MASTER_INDEX.md`](docs/audit/00_MASTER_INDEX.md)**

## 🗺️ 开发路线图

### ✅ v2.0.0-beta.2（当前 — 2026 年 3 月）
- [x] 从 Python 完全重写为 Go
- [x] 三策略提取引擎
- [x] 动态 Cookie 生成
- [x] H264 + H265 双编码 × FLV + HLS 格式
- [x] 交互式画质选择器（26+ 路流）
- [x] FFmpeg 录制（`-c copy`）+ 自动文件名
- [x] mpv + ffplay 播放 + 硬件加速
- [x] 全平台编译（Linux、macOS、Windows）
- [x] CI 流水线 + 发布自动化
- [x] 军事级代码审计（28 份报告）

### 🔜 v2.1.0（计划中 — 稳定性加固）
- [ ] 修复并发数据竞争（`sync.RWMutex`）
- [ ] FFmpeg 优雅关闭（`SIGINT` 替代 `SIGKILL`）
- [ ] 配置系统（TOML/Viper）
- [ ] HTTP 重试逻辑 + 指数退避
- [ ] 供应链安全加固

### 🔮 v2.2.0+（未来 — 高级功能）
- [ ] 原生 Go DVR 引擎（消除 FFmpeg 依赖）
- [ ] TLS 指纹伪装（`uTLS`）
- [ ] WebSocket 弹幕/礼物捕获
- [ ] 多 CDN 动态切换
- [ ] 直传 S3 录制（Cloudflare R2 / Backblaze B2）

## 🧰 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Go 1.25（静态二进制，零运行时依赖） |
| CLI 框架 | [Cobra](https://github.com/spf13/cobra) |
| HTTP 客户端 | `net/http` + 浏览器请求头伪装 |
| 播放 | `mpv`、`ffplay`（通过 `os/exec`） |
| 录制 | `ffmpeg`（通过 `os/exec`，`-c copy`） |
| 构建系统 | `Makefile` + `go build -trimpath -ldflags` |
| CI/CD | GitHub Actions（3 操作系统矩阵 + 交叉编译） |
| 版本管理 | SemVer + Git 标签（`v2.0.0-beta.2`） |

## 📝 致谢

- [caiguanhao/dylive](https://github.com/caiguanhao/dylive) (MIT) — `__pace_f` 解析方案
- [iawia002/lux](https://github.com/iawia002/lux) (MIT) — Cookie 生成方案
- [douyinstream-pro](https://github.com/JairFC/douyinstream-pro) — 原始 Python 版本

## ⚖️ 许可证

MIT License — 详见 [LICENSE](LICENSE)。

> **免责声明**: 本工具仅供教育和个人使用。不涉及 DRM 破解或加密绕过。
> 直播流地址公开嵌入在抖音的 HTML 源码中。请尊重内容创作者和抖音的服务条款。
