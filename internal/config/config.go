// Package config manages application configuration via TOML files.
package config

import (
	"os"
	"path/filepath"
	"runtime"
)

// Config holds all application configuration.
type Config struct {
	Player    PlayerConfig    `toml:"player"`
	Quality   QualityConfig   `toml:"quality"`
	Recording RecordingConfig `toml:"recording"`
	Cookies   CookieConfig    `toml:"cookies"`
	Network   NetworkConfig   `toml:"network"`
}

// PlayerConfig configures video playback.
type PlayerConfig struct {
	Preferred string `toml:"preferred"` // "mpv" or "ffplay"
	MPVPath   string `toml:"mpv_path"`  // Custom mpv path (auto-detect if empty)
}

// QualityConfig configures stream quality selection.
type QualityConfig struct {
	Default  string `toml:"default"`  // uhd, origin, hd, sd, ld
	Fallback string `toml:"fallback"` // "best" to auto-select
}

// RecordingConfig configures DVR/recording behavior.
type RecordingConfig struct {
	DownloadDir      string `toml:"download_dir"`
	BufferMinutes    int    `toml:"buffer_minutes"`
	SegmentDuration  int    `toml:"segment_duration_sec"`
}

// CookieConfig configures cookie sourcing.
type CookieConfig struct {
	Source   string `toml:"source"`    // auto, browser, file, dynamic
	Browser  string `toml:"browser"`   // chrome, edge, firefox (auto if empty)
	FilePath string `toml:"file_path"` // Path to cookies file
}

// NetworkConfig configures HTTP behavior.
type NetworkConfig struct {
	TimeoutSec int    `toml:"timeout_sec"`
	RetryCount int    `toml:"retry_count"`
	UserAgent  string `toml:"user_agent"`
}

// Default returns a Config with sensible defaults.
func Default() *Config {
	return &Config{
		Player: PlayerConfig{
			Preferred: "mpv",
		},
		Quality: QualityConfig{
			Default:  "uhd",
			Fallback: "best",
		},
		Recording: RecordingConfig{
			DownloadDir:     defaultDownloadDir(),
			BufferMinutes:   3,
			SegmentDuration: 10,
		},
		Cookies: CookieConfig{
			Source: "auto",
		},
		Network: NetworkConfig{
			TimeoutSec: 15,
			RetryCount: 3,
		},
	}
}

// CacheDir returns the application cache directory.
func CacheDir() string {
	switch runtime.GOOS {
	case "windows":
		return filepath.Join(os.Getenv("LOCALAPPDATA"), "douyinstream")
	case "darwin":
		home, _ := os.UserHomeDir()
		return filepath.Join(home, "Library", "Caches", "douyinstream")
	default:
		cacheDir := os.Getenv("XDG_CACHE_HOME")
		if cacheDir == "" {
			home, _ := os.UserHomeDir()
			cacheDir = filepath.Join(home, ".cache")
		}
		return filepath.Join(cacheDir, "douyinstream")
	}
}

// ConfigDir returns the application config directory.
func ConfigDir() string {
	switch runtime.GOOS {
	case "windows":
		return filepath.Join(os.Getenv("APPDATA"), "douyinstream")
	case "darwin":
		home, _ := os.UserHomeDir()
		return filepath.Join(home, "Library", "Application Support", "douyinstream")
	default:
		configDir := os.Getenv("XDG_CONFIG_HOME")
		if configDir == "" {
			home, _ := os.UserHomeDir()
			configDir = filepath.Join(home, ".config")
		}
		return filepath.Join(configDir, "douyinstream")
	}
}

func defaultDownloadDir() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, "Downloads", "Douyin_Rips")
}
