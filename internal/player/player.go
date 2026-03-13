// Package player handles video playback via external players (mpv, ffplay).
package player

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

// Player defines the interface for video playback.
type Player interface {
	Name() string
	Available() bool
	Play(ctx context.Context, url string, opts PlayOptions) error
}

// PlayOptions configures playback behavior.
type PlayOptions struct {
	Title        string // Window title
	Quality      string // Quality label for OSD
	RecordPath   string // If set, record the stream to this file
	Fullscreen   bool   // Start in fullscreen mode
	ExtraArgs    []string // Additional player-specific arguments
}

// Detect finds the best available player on the system.
func Detect() Player {
	// Try mpv first (preferred)
	mpv := &MPVPlayer{}
	if mpv.Available() {
		slog.Info("detected player", "name", "mpv", "path", mpv.path())
		return mpv
	}

	// Try ffplay as fallback
	ffp := &FFPlayPlayer{}
	if ffp.Available() {
		slog.Info("detected player", "name", "ffplay", "path", ffp.path())
		return ffp
	}

	slog.Warn("no video player found — install mpv for best experience")
	return nil
}

// DetectByName tries to find a specific player by name.
func DetectByName(name string) Player {
	switch strings.ToLower(name) {
	case "mpv":
		p := &MPVPlayer{}
		if p.Available() {
			return p
		}
	case "ffplay":
		p := &FFPlayPlayer{}
		if p.Available() {
			return p
		}
	}
	return nil
}

// --------------------------------------------------------------------------
// mpv Player — Primary player with IPC support
// --------------------------------------------------------------------------

// MPVPlayer uses mpv for high-quality video playback.
type MPVPlayer struct {
	customPath string
}

func (p *MPVPlayer) Name() string { return "mpv" }

func (p *MPVPlayer) Available() bool {
	return p.path() != ""
}

func (p *MPVPlayer) path() string {
	if p.customPath != "" {
		if _, err := os.Stat(p.customPath); err == nil {
			return p.customPath
		}
	}

	// Check PATH
	path, err := exec.LookPath("mpv")
	if err == nil {
		return path
	}

	// Platform-specific common locations
	switch runtime.GOOS {
	case "windows":
		candidates := []string{
			filepath.Join(os.Getenv("PROGRAMFILES"), "mpv", "mpv.exe"),
			filepath.Join(os.Getenv("LOCALAPPDATA"), "Programs", "mpv", "mpv.exe"),
			`C:\mpv\mpv.exe`,
		}
		for _, c := range candidates {
			if _, err := os.Stat(c); err == nil {
				return c
			}
		}
	case "darwin":
		candidates := []string{
			"/opt/homebrew/bin/mpv",
			"/usr/local/bin/mpv",
			"/Applications/mpv.app/Contents/MacOS/mpv",
		}
		for _, c := range candidates {
			if _, err := os.Stat(c); err == nil {
				return c
			}
		}
	}

	return ""
}

func (p *MPVPlayer) Play(ctx context.Context, url string, opts PlayOptions) error {
	mpvPath := p.path()
	if mpvPath == "" {
		return fmt.Errorf("mpv not found")
	}

	args := []string{
		url,
		"--force-seekable=yes",
		"--cache=yes",
		"--cache-secs=30",
		"--demuxer-max-bytes=500MiB",
		"--demuxer-readahead-secs=20",
	}

	// Window title
	if opts.Title != "" {
		args = append(args, fmt.Sprintf("--title=%s", opts.Title))
	}

	// Quality OSD message
	if opts.Quality != "" {
		args = append(args, fmt.Sprintf("--osd-msg1=Quality: %s", opts.Quality))
	}

	// Record stream while playing
	if opts.RecordPath != "" {
		args = append(args, fmt.Sprintf("--stream-record=%s", opts.RecordPath))
	}

	// Fullscreen
	if opts.Fullscreen {
		args = append(args, "--fullscreen")
	}

	// Hardware decoding
	args = append(args, "--hwdec=auto-safe")

	// Extra arguments
	args = append(args, opts.ExtraArgs...)

	slog.Info("launching mpv",
		"path", mpvPath,
		"url", truncateURL(url, 80),
		"record", opts.RecordPath != "",
	)

	cmd := exec.CommandContext(ctx, mpvPath, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		// mpv returns non-zero when user closes the window — that's fine
		if ctx.Err() != nil {
			return nil // Context cancelled
		}
		return fmt.Errorf("mpv exited with error: %w", err)
	}

	return nil
}

// --------------------------------------------------------------------------
// ffplay Player — Fallback (minimal controls)
// --------------------------------------------------------------------------

// FFPlayPlayer uses ffplay as a basic fallback player.
type FFPlayPlayer struct {
	customPath string
}

func (p *FFPlayPlayer) Name() string { return "ffplay" }

func (p *FFPlayPlayer) Available() bool {
	return p.path() != ""
}

func (p *FFPlayPlayer) path() string {
	if p.customPath != "" {
		if _, err := os.Stat(p.customPath); err == nil {
			return p.customPath
		}
	}

	path, err := exec.LookPath("ffplay")
	if err == nil {
		return path
	}

	return ""
}

func (p *FFPlayPlayer) Play(ctx context.Context, url string, opts PlayOptions) error {
	ffplayPath := p.path()
	if ffplayPath == "" {
		return fmt.Errorf("ffplay not found")
	}

	args := []string{
		"-infbuf",
		"-fflags", "nobuffer",
		"-flags", "low_delay",
		"-analyzeduration", "500000",
		url,
	}

	if opts.Title != "" {
		args = append(args, "-window_title", opts.Title)
	}

	if opts.Fullscreen {
		args = append(args, "-fs")
	}

	slog.Info("launching ffplay",
		"path", ffplayPath,
		"url", truncateURL(url, 80),
	)

	cmd := exec.CommandContext(ctx, ffplayPath, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		if ctx.Err() != nil {
			return nil
		}
		return fmt.Errorf("ffplay exited with error: %w", err)
	}

	return nil
}

// --------------------------------------------------------------------------
// Helpers
// --------------------------------------------------------------------------

func truncateURL(url string, maxLen int) string {
	if len(url) <= maxLen {
		return url
	}
	return url[:maxLen] + "..."
}
