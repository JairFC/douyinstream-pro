// DouyinStream Go — Watch Douyin live streams at maximum quality.
//
// A cross-platform CLI tool that extracts Douyin live stream URLs at the
// highest available quality (UHD/1080p60+) without requiring a Chinese
// account, and plays them via mpv.
//
// Credits: Inspired by douyinstream-pro (Python), with extraction patterns
// adapted from caiguanhao/dylive (MIT) and iawia002/lux (MIT).
package main

import (
	"bufio"
	"context"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/JairFC/douyinstream-go/internal/config"
	"github.com/JairFC/douyinstream-go/internal/cookie"
	"github.com/JairFC/douyinstream-go/internal/extractor"
	"github.com/JairFC/douyinstream-go/internal/platform"
	"github.com/JairFC/douyinstream-go/internal/player"
	"github.com/JairFC/douyinstream-go/pkg/httpclient"

	"github.com/spf13/cobra"
)

var (
	version   = "0.1.0-dev"
	commit    = "unknown"
	buildTime = "unknown"

	// Global flags
	flagQuality string
	flagPlayer  string
	flagVerbose bool
	flagRecord  string
	flagSelect  bool
)

func main() {
	rootCmd := &cobra.Command{
		Use:   "douyinstream",
		Short: "🎬 Watch Douyin live streams at maximum quality",
		Long: `DouyinStream Go — Watch Douyin live streams at the highest available quality.

Extracts stream URLs from Douyin live rooms and plays them via mpv,
bypassing the web player's quality restrictions. No account needed.

Examples:
  douyinstream play https://live.douyin.com/94782239787
  douyinstream play --quality uhd https://live.douyin.com/94782239787
  douyinstream play --select https://live.douyin.com/94782239787
  douyinstream extract https://live.douyin.com/94782239787
  douyinstream play --record output.mp4 https://live.douyin.com/94782239787`,
		Version: version,
	}

	// Global flags
	rootCmd.PersistentFlags().StringVarP(&flagQuality, "quality", "q", "uhd", "Stream quality: origin, uhd, hd, sd, ld")
	rootCmd.PersistentFlags().StringVarP(&flagPlayer, "player", "p", "", "Player to use: mpv, ffplay (auto-detect if empty)")
	rootCmd.PersistentFlags().BoolVarP(&flagVerbose, "verbose", "v", false, "Enable verbose logging")
	rootCmd.PersistentFlags().StringVarP(&flagRecord, "record", "r", "", "Record stream to file while playing")
	rootCmd.PersistentFlags().BoolVarP(&flagSelect, "select", "s", false, "Interactively select quality before playing")

	// Commands
	rootCmd.AddCommand(playCmd())
	rootCmd.AddCommand(extractCmd())
	rootCmd.AddCommand(recordCmd())

	if err := rootCmd.Execute(); err != nil {
		os.Exit(1)
	}
}

func playCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "play <url>",
		Short: "Extract and play a Douyin live stream",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			setupLogging()

			ctx, cancel := signal.NotifyContext(context.Background(),
				syscall.SIGINT, syscall.SIGTERM)
			defer cancel()

			url := args[0]

			// 1. Extract stream URL
			result, err := extractStream(ctx, url)
			if err != nil {
				return err
			}

			// 2. Check if stream is live
			if !result.IsLive || result.URL == "" {
				fmt.Println("\n⏸️  This stream is currently offline. No video to play.")
				fmt.Println("   Use 'douyinstream extract' to see room info.")
				return nil
			}

			// 3. Select quality — interactive or flag-based
			var streamURL string
			var qualityLabel string

			if flagSelect {
				selected := selectQualityInteractive(result)
				if selected == nil {
					fmt.Println("Cancelled.")
					return nil
				}
				streamURL = selected.URL
				qualityLabel = selected.Label
			} else {
				streamURL = result.QualityURL(flagQuality)
				qualityLabel = flagQuality
			}

			fmt.Printf("✨ Playing %s...\n", qualityLabel)

			// 4. Find player
			p := findPlayer()
			if p == nil {
				fmt.Println("\n❌ No video player found!")
				fmt.Println("   Install mpv: https://mpv.io/installation/")
				fmt.Println("   Or ffplay (comes with FFmpeg)")
				return fmt.Errorf("no video player available")
			}
			fmt.Printf("🖥️  Opening %s...\n\n", p.Name())

			// 5. Play
			opts := player.PlayOptions{
				Title:      fmt.Sprintf("DouyinStream — %s by %s", result.Title, result.Author),
				Quality:    qualityLabel,
				RecordPath: flagRecord,
			}

			return p.Play(ctx, streamURL, opts)
		},
	}
}

func extractCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "extract <url>",
		Short: "Extract stream URLs without playing",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			setupLogging()

			ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
			defer cancel()

			result, err := extractStream(ctx, args[0])
			if err != nil {
				return err
			}

			// Print results
			fmt.Println()
			fmt.Printf("📡 Stream: %s\n", result.Title)
			fmt.Printf("👤 Author: %s\n", result.Author)
			fmt.Printf("🔴 Live:   %v\n", result.IsLive)
			fmt.Printf("🆔 Room:   %s\n", result.RoomID)
			fmt.Println()

			// Show sorted quality list
			qualities := result.SortedQualities()
			if len(qualities) > 0 {
				fmt.Println("📺 Available qualities:")
				for i, q := range qualities {
					fmt.Printf("  %2d. %-30s %s\n", i+1, q.Label, truncateForDisplay(q.URL, 55))
				}
			}

			fmt.Println()
			fmt.Printf("🏆 Best URL:\n  %s\n", result.BestQualityURL())

			return nil
		},
	}
}

func recordCmd() *cobra.Command {
	var flagOutput string

	cmd := &cobra.Command{
		Use:   "record <url>",
		Short: "Record a Douyin live stream to a file",
		Long: `Record a live stream directly to a file without opening a player.
Uses ffmpeg for zero-overhead recording (stream copy, no re-encoding).

Examples:
  douyinstream record https://live.douyin.com/94782239787
  douyinstream record -o stream.mp4 https://live.douyin.com/94782239787
  douyinstream record -q origin -o best.flv https://live.douyin.com/94782239787
  douyinstream record --select https://live.douyin.com/94782239787`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			setupLogging()

			ctx, cancel := signal.NotifyContext(context.Background(),
				syscall.SIGINT, syscall.SIGTERM)
			defer cancel()

			url := args[0]

			// 1. Extract
			result, err := extractStream(ctx, url)
			if err != nil {
				return err
			}

			if !result.IsLive || result.URL == "" {
				fmt.Println("\n⏸️  This stream is currently offline. Nothing to record.")
				return nil
			}

			// 2. Select quality
			var streamURL string
			var qualityLabel string

			if flagSelect {
				selected := selectQualityInteractive(result)
				if selected == nil {
					fmt.Println("Cancelled.")
					return nil
				}
				streamURL = selected.URL
				qualityLabel = selected.Label
			} else {
				streamURL = result.QualityURL(flagQuality)
				qualityLabel = flagQuality
			}

			// 3. Determine output filename
			if flagOutput == "" {
				// Auto-generate: author_timestamp.flv
				ts := time.Now().Format("20060102_150405")
				safeAuthor := strings.Map(func(r rune) rune {
					if r == '/' || r == '\\' || r == ':' || r == ' ' {
						return '_'
					}
					return r
				}, result.Author)
				ext := ".flv"
				if strings.Contains(streamURL, ".m3u8") {
					ext = ".mp4"
				}
				flagOutput = fmt.Sprintf("%s_%s%s", safeAuthor, ts, ext)
			}

			fmt.Printf("⏺️  Recording %s to: %s\n", qualityLabel, flagOutput)
			fmt.Println("   Press Ctrl+C to stop recording.")
			fmt.Println()

			// 4. Record using ffmpeg (preferred) or mpv --stream-record
			ffmpegPath, err := exec.LookPath("ffmpeg")
			if err == nil {
				return recordWithFFmpeg(ctx, ffmpegPath, streamURL, flagOutput)
			}

			// Fallback: try mpv --stream-record
			p := findPlayer()
			if p != nil && p.Name() == "mpv" {
				fmt.Println("⚠️  ffmpeg not found — using mpv for recording")
				opts := player.PlayOptions{
					Title:      fmt.Sprintf("DouyinStream Recording — %s", result.Author),
					Quality:    qualityLabel,
					RecordPath: flagOutput,
				}
				return p.Play(ctx, streamURL, opts)
			}

			return fmt.Errorf("recording requires ffmpeg or mpv. Install ffmpeg: sudo apt install ffmpeg")
		},
	}

	cmd.Flags().StringVarP(&flagOutput, "output", "o", "", "Output file path (auto-generated if empty)")

	return cmd
}

// recordWithFFmpeg records a stream URL to a file using ffmpeg -c copy (no re-encoding).
func recordWithFFmpeg(ctx context.Context, ffmpegPath, streamURL, output string) error {
	args := []string{
		"-i", streamURL,
		"-c", "copy", // No re-encoding — direct stream copy
		"-movflags", "+faststart", // Optimize for playback
		"-y", // Overwrite output
		output,
	}

	slog.Info("launching ffmpeg recording",
		"output", output,
		"url_len", len(streamURL),
	)

	cmd := exec.CommandContext(ctx, ffmpegPath, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		if ctx.Err() != nil {
			// User pressed Ctrl+C — recording was intentionally stopped
			fmt.Printf("\n✅ Recording saved to: %s\n", output)
			return nil
		}
		return fmt.Errorf("ffmpeg error: %w", err)
	}

	fmt.Printf("\n✅ Recording saved to: %s\n", output)
	return nil
}

// selectQualityInteractive shows an interactive menu to pick quality.
func selectQualityInteractive(result *extractor.StreamResult) *extractor.QualityInfo {
	qualities := result.SortedQualities()
	if len(qualities) == 0 {
		return nil
	}

	fmt.Println()
	fmt.Println("📺 Select stream quality:")
	fmt.Println(strings.Repeat("─", 50))

	for i, q := range qualities {
		bestMarker := "  "
		if i == 0 {
			bestMarker = "★ "
		}
		fmt.Printf("  %s%2d. %s\n", bestMarker, i+1, q.Label)
	}

	fmt.Println(strings.Repeat("─", 50))
	fmt.Printf("  Enter number [1-%d] (default: 1): ", len(qualities))

	scanner := bufio.NewScanner(os.Stdin)
	if !scanner.Scan() {
		return nil
	}

	input := strings.TrimSpace(scanner.Text())

	// Default to first (best quality)
	if input == "" {
		selected := qualities[0]
		return &selected
	}

	choice, err := strconv.Atoi(input)
	if err != nil || choice < 1 || choice > len(qualities) {
		fmt.Printf("❌ Invalid choice: %s\n", input)
		return nil
	}

	selected := qualities[choice-1]
	return &selected
}

// extractStream is the core extraction pipeline used by all commands.
func extractStream(ctx context.Context, rawURL string) (*extractor.StreamResult, error) {
	// Detect platform
	plat := platform.Detect(rawURL)
	if plat != platform.PlatformDouyin {
		return nil, fmt.Errorf("unsupported platform: %s (only Douyin is supported currently)", plat)
	}

	fmt.Printf("🔍 Extracting stream URL...\n")

	// Resolve short URLs
	if platform.IsShortURL(rawURL) {
		fmt.Printf("🔗 Resolving short URL...\n")
		client := httpclient.New()
		resolved, err := client.ResolveShortURL(ctx, rawURL)
		if err != nil {
			return nil, fmt.Errorf("resolving short URL: %w", err)
		}
		rawURL = resolved
		slog.Info("resolved short URL", "resolved", rawURL)
	}

	// Generate cookies
	cookies, err := cookie.GenerateDynamic(ctx)
	if err != nil {
		slog.Warn("failed to generate dynamic cookies", "error", err)
		cookies = &cookie.Cookies{
			AcNonce: "064caded4009deafd8b89",
		}
	}

	// Fetch page
	client := httpclient.New(
		httpclient.WithCookies(cookies.ToMap()),
	)

	html, err := client.Get(ctx, rawURL)
	if err != nil {
		return nil, fmt.Errorf("fetching page: %w", err)
	}

	slog.Info("fetched page", "size", len(html))

	// Check for CAPTCHA
	if extractor.IsCaptchaPage(html) {
		fmt.Println("⚠️  CAPTCHA detected! Manual cookie setup may be needed.")
		fmt.Println("   Try: douyinstream play --cookies browser <url>")
		return nil, fmt.Errorf("CAPTCHA detected — see above for instructions")
	}

	// Check for empty/small page
	if len(html) < 10000 {
		return nil, fmt.Errorf("page too small (%d bytes) — stream may be offline or authentication needed", len(html))
	}

	// Extract stream URLs
	ext := extractor.New(config.CacheDir())

	result, err := ext.Extract(html)
	if err != nil {
		return nil, fmt.Errorf("extraction failed: %w", err)
	}

	fmt.Printf("📡 Found: \"%s\" by %s\n", result.Title, result.Author)

	if !result.IsLive {
		fmt.Println("⏸️  Stream is currently OFFLINE")
	}

	// List available qualities
	if len(result.Qualities) > 0 {
		qualityNames := make([]string, 0, len(result.Qualities))
		for name := range result.Qualities {
			qualityNames = append(qualityNames, name)
		}
		fmt.Printf("🎬 Qualities: %s\n", strings.Join(qualityNames, ", "))
	}

	return result, nil
}

func findPlayer() player.Player {
	if flagPlayer != "" {
		return player.DetectByName(flagPlayer)
	}
	return player.Detect()
}

func setupLogging() {
	level := slog.LevelWarn
	if flagVerbose {
		level = slog.LevelDebug
	}

	handler := slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{
		Level: level,
	})
	slog.SetDefault(slog.New(handler))
}

func truncateForDisplay(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}
