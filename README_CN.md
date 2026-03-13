# 🎬 DouyinStream Go

> 以最高画质观看抖音直播 — 无需登录账号

[English](README.md) | **中文**

跨平台命令行工具，从抖音直播间提取最高画质的直播流（原画/蓝光/1080p60+），
绕过网页播放器的画质限制。支持 **H264 和 H265** 双编码，每个直播间可提取多达 **26 路流**。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ 功能特性

- 🔓 **无需账号** — 动态生成 Cookie，不需要中国手机号
- 📺 **全部画质** — 提取原画、蓝光、超清、高清、标清 + 纯音频
- 🎥 **H264 + H265** — 双编码提取，含完整元数据（分辨率、帧率、码率）
- 🎛️ **交互式画质选择** — 自由选择播放哪路流
- ⏺️ **录制** — 使用 ffmpeg 保存直播流（零开销，无需重编码）
- 🖥️ **mpv + ffplay** — 外置播放器，支持硬件加速
- 🌐 **全平台** — Linux、macOS、Windows 单文件可执行
- 📦 **约 6MB** — 无运行时依赖（Go 静态编译）
- ⚡ **自适应提取** — 3 种策略级联，确保解析成功

## 🚀 快速开始

```bash
# 从源码编译
git clone https://github.com/JairFC/douyinstream-go
cd douyinstream-go
make build

# 提取直播流信息
./bin/douyinstream extract https://live.douyin.com/直播间ID

# 以最高画质播放
./bin/douyinstream play https://live.douyin.com/直播间ID

# 交互式选择画质
./bin/douyinstream play --select https://live.douyin.com/直播间ID

# 录制直播流
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
```

## 🎮 命令说明

### `play` — 观看直播

```bash
# 自动选择最高画质
douyinstream play https://live.douyin.com/直播间ID

# 指定画质
douyinstream play -q origin https://live.douyin.com/直播间ID

# 交互式选择
douyinstream play --select https://live.douyin.com/直播间ID

# 边看边录
douyinstream play -r output.mp4 https://live.douyin.com/直播间ID
```

### `extract` — 获取直播流地址

```bash
# 显示所有可用画质、编码、格式和地址
douyinstream extract https://live.douyin.com/直播间ID
```

### `record` — 录制直播

```bash
# 自动生成文件名
douyinstream record https://live.douyin.com/直播间ID
# → 主播名_20260313_120000.flv

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

## 🛠️ 编译安装

### 环境要求

- Go 1.21+
- 可选: `mpv` 或 `ffplay`（用于播放）
- 可选: `ffmpeg`（用于录制）

### 从源码编译

```bash
make build          # 编译当前平台
make build-all      # 全平台交叉编译
make release        # 构建发布包
```

### 预编译文件

从 [Releases](https://github.com/JairFC/douyinstream-pro/releases) 下载：

| 平台 | 文件 |
|------|------|
| Linux x64 | `douyinstream-linux-amd64` |
| Linux ARM64 | `douyinstream-linux-arm64` |
| macOS Intel | `douyinstream-darwin-amd64` |
| macOS Apple Silicon | `douyinstream-darwin-arm64` |
| Windows x64 | `douyinstream-windows-amd64.exe` |

## 🔧 工作原理

抖音在直播页面的 HTML 中将**所有画质的直播流地址**嵌入到 `__pace_f` JavaScript 块中。
网页播放器通过前端代码限制未登录用户只能观看标清画质，但所有画质的地址实际上已经在页面源码中。

DouyinStream 的工作流程：
1. **动态生成 Cookie**（`msToken`、`ttwid`），无需浏览器
2. 使用浏览器模拟的请求头**获取页面**
3. 从 `__pace_f.push()` 块中**解析嵌入的 JSON**
4. 提取 H264/H265 × FLV/HLS × 7 个画质等级的**全部 26+ 路流地址**
5. **选择最高画质**（优先原画 H265 FLV）
6. 通过 **mpv/ffplay 播放**或通过 **ffmpeg 录制**

## 📝 致谢

- [caiguanhao/dylive](https://github.com/caiguanhao/dylive) (MIT) — `__pace_f` 解析方案
- [iawia002/lux](https://github.com/iawia002/lux) (MIT) — Cookie 生成方案
- [douyinstream-pro](https://github.com/JairFC/douyinstream-pro) — 原始 Python 版本

## ⚖️ 许可证

MIT License — 详见 [LICENSE](LICENSE)。

> **免责声明**: 本工具仅供教育和个人使用。不涉及 DRM 破解或加密绕过。
> 直播流地址公开嵌入在抖音的 HTML 源码中。请尊重内容创作者和抖音的服务条款。
