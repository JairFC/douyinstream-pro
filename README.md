# DouyinStream Pro 🎬

A modern, open-source desktop application for watching Douyin/TikTok live streams with advanced features.

> ⚠️ **Disclaimer**: This is a free, open-source project for educational purposes only. Not for commercial use.

## Features

- 🎥 **Embedded VLC Player** - Watch streams directly in the app
- 📋 **Clipboard Detection** - Auto-detect Douyin/TikTok URLs
- 💾 **Clip Buffer** - Save the last N minutes of stream
- 🔴 **Recording** - Record full streams
- ⭐ **Favorites** - Save your favorite streamers
- 🎬 **Cinema Mode** - Borderless fullscreen experience (F11)
- 🎨 **Modern UI** - Dark theme with customtkinter

## Requirements

- Python 3.9+
- VLC Media Player (64-bit)
- FFmpeg (for recording)

## Installation

```bash
# Clone the repository
git clone https://github.com/JairFC/douyingproject.git
cd douyingproject

# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py
```

## Dependencies

- customtkinter
- streamlink
- python-vlc
- Pillow

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| F11 | Toggle Cinema Mode |
| ESC | Exit Cinema Mode |
| Space | Play/Pause (fullscreen) |

## License

MIT License - Free and open source.

## Author

- **JairFC** - [GitHub](https://github.com/JairFC)

---

*v0.1-alpha* - Initial release
