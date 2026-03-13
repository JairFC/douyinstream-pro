// Package extractor implements multi-strategy stream URL extraction for Douyin.
// It uses an adaptive approach that tries multiple extraction strategies and
// caches the last working one for optimized subsequent calls.
package extractor

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

// StreamResult contains the extracted stream information.
type StreamResult struct {
	URL          string                   `json:"url"`           // Best quality stream URL
	Title        string                   `json:"title"`         // Stream title
	Author       string                   `json:"author"`        // Streamer nickname
	IsLive       bool                     `json:"is_live"`       // Whether the stream is currently live
	Qualities    map[string]string        `json:"qualities"`     // Quality name -> URL mapping
	QualityMeta  map[string]QualityMeta   `json:"quality_meta"`  // Metadata per quality (resolution, fps, bitrate, codec)
	RoomID       string                   `json:"room_id"`       // Room identifier
}

// QualityMeta holds technical metadata for a stream quality option.
type QualityMeta struct {
	Width   int    `json:"width"`    // Video width (e.g. 1920)
	Height  int    `json:"height"`   // Video height (e.g. 1080)
	FPS     int    `json:"fps"`      // Frames per second (e.g. 60, 120)
	Bitrate int    `json:"bitrate"`  // Video bitrate in bps (e.g. 14778000)
	Codec   string `json:"codec"`    // Video codec ("h264" or "h265")
}

// QualityInfo holds display-friendly info about a stream quality option.
type QualityInfo struct {
	Name   string // Internal name (e.g. "FULL_HD1")
	Label  string // Display label (e.g. "🔵 FULL_HD (UHD)")
	Format string // "FLV" or "HLS"
	Tier   int    // Sort priority (lower = better quality)
	URL    string // Stream URL
}

// qualityTiers defines the display order and labels for known quality names.
var qualityTiers = []struct {
	contains string
	label    string
	tier     int
}{
	{"origin", "原画 Origin", 0},
	{"FULL_HD", "蓝光 UHD", 1},
	{"uhd", "蓝光 UHD", 1},
	{"HD1", "超清 HD", 3},
	{"hd_", "超清 HD", 3},
	{"SD1", "高清 SD", 4},
	{"SD2", "标清 SD Low", 5},
	{"sd", "SD", 4},
	{"LD", "标清 LD", 6},
	{"ld_", "标清 LD", 6},
	{"md_", "流畅 MD", 7},
	{"ao_", "Audio Only", 8},
}

// SortedQualities returns all qualities sorted for display:
// FLV first (preferred), then HLS; H265 before H264; each sorted by tier.
func (sr *StreamResult) SortedQualities() []QualityInfo {
	if sr == nil || len(sr.Qualities) == 0 {
		return nil
	}

	var infos []QualityInfo
	for name, url := range sr.Qualities {
		format := "FLV"
		if strings.Contains(name, "_hls") || strings.HasSuffix(url, ".m3u8") || strings.Contains(url, ".m3u8?") {
			format = "HLS"
		}

		tier := 99
		label := name
		for _, t := range qualityTiers {
			if strings.Contains(name, t.contains) {
				label = t.label
				tier = t.tier
				break
			}
		}

		// Detect codec from key name
		codec := ""
		if strings.Contains(name, "h265") {
			codec = "H265"
		} else if strings.Contains(name, "h264") {
			codec = "H264"
		}

		// Emoji indicator by tier
		emoji := "⚪"
		switch {
		case tier <= 0:
			emoji = "🟣" // Origin (highest)
		case tier <= 1:
			emoji = "🔵" // UHD
		case tier <= 3:
			emoji = "🟡" // HD
		case tier <= 5:
			emoji = "🟠" // SD
		case tier <= 7:
			emoji = "🔴" // LD / MD
		default:
			emoji = "⚫" // Audio only / unknown
		}

		// Build label with specs when available
		specs := ""
		if sr.QualityMeta != nil {
			if meta, ok := sr.QualityMeta[name]; ok && meta.Height > 0 {
				specs = fmt.Sprintf(" %dx%d", meta.Width, meta.Height)
				if meta.FPS > 0 {
					specs += fmt.Sprintf(" %dfps", meta.FPS)
				}
				if meta.Bitrate > 0 {
					specs += fmt.Sprintf(" %dkbps", meta.Bitrate/1000)
				}
				if codec == "" && meta.Codec != "" {
					codec = strings.ToUpper(meta.Codec)
				}
			}
		}

		codecStr := ""
		if codec != "" {
			codecStr = " " + codec
		}

		infos = append(infos, QualityInfo{
			Name:   name,
			Label:  fmt.Sprintf("%s %s (%s%s)%s", emoji, label, format, codecStr, specs),
			Format: format,
			Tier:   tier,
			URL:    url,
		})
	}

	// Sort: FLV before HLS, then by tier, then H265 before H264
	sort.Slice(infos, func(i, j int) bool {
		// FLV first
		if infos[i].Format != infos[j].Format {
			return infos[i].Format == "FLV"
		}
		// Better quality first
		if infos[i].Tier != infos[j].Tier {
			return infos[i].Tier < infos[j].Tier
		}
		// H265 before H264 (better quality at same tier)
		ih265 := strings.Contains(infos[i].Name, "h265")
		jh265 := strings.Contains(infos[j].Name, "h265")
		if ih265 != jh265 {
			return ih265
		}
		return infos[i].Name < infos[j].Name
	})

	return infos
}

// BestQualityURL returns the stream URL for the highest available quality.
// Priority: origin > uhd > hd > sd > ld, H265 preferred over H264, FLV over HLS.
func (sr *StreamResult) BestQualityURL() string {
	if sr == nil || len(sr.Qualities) == 0 {
		return sr.URL
	}

	// Ordered priority: best first
	bestKeys := []string{
		"origin_h265_flv", "origin_h264_flv",
		"uhd_h265_flv", "uhd_h264_flv",
		"FULL_HD1",
		"hd_h265_flv", "hd_h264_flv",
		"HD1",
		"sd_h265_flv", "sd_h264_flv",
		"SD1", "SD2",
		"origin_h265_hls", "origin_h264_hls",
		"uhd_h265_hls", "uhd_h264_hls",
	}

	for _, key := range bestKeys {
		if url, ok := sr.Qualities[key]; ok {
			return url
		}
	}

	// Fallback: search by partial match
	priorities := []string{"origin", "uhd", "FULL_HD", "hd", "HD1", "sd", "SD1"}
	for _, p := range priorities {
		for qName, qURL := range sr.Qualities {
			if strings.Contains(qName, p) {
				return qURL
			}
		}
	}

	// Last resort: first available
	for _, url := range sr.Qualities {
		return url
	}

	return sr.URL
}

// QualityURL returns the URL for a specific quality, or the best available.
// Accepts: "origin", "uhd", "hd", "sd", "ld" — will prefer H265 FLV.
func (sr *StreamResult) QualityURL(quality string) string {
	if sr == nil || len(sr.Qualities) == 0 {
		return sr.URL
	}

	quality = strings.ToLower(quality)

	// Try exact match first (new format + old format)
	tryKeys := []string{
		quality + "_h265_flv",
		quality + "_h264_flv",
		quality + "_h265_hls",
		quality + "_h264_hls",
	}

	for _, key := range tryKeys {
		if url, ok := sr.Qualities[key]; ok {
			return url
		}
	}

	// Alias mapping for old-style keys
	aliasMap := map[string][]string{
		"uhd":    {"FULL_HD1", "uhd"},
		"origin": {"ORIGION", "origin"},
		"hd":     {"HD1", "hd"},
		"sd":     {"SD1", "SD2", "sd"},
		"ld":     {"LD", "ld"},
	}

	if aliases, ok := aliasMap[quality]; ok {
		for _, alias := range aliases {
			for qName, qURL := range sr.Qualities {
				if strings.Contains(qName, alias) {
					return qURL
				}
			}
		}
	}

	return sr.BestQualityURL()
}

// Strategy defines the interface for stream extraction approaches.
type Strategy interface {
	Name() string
	Priority() int
	CanExtract(html string) bool
	Extract(html string) (*StreamResult, error)
}

// strategyStats tracks success/failure counts for a strategy.
type strategyStats struct {
	Successes int `json:"successes"`
	Failures  int `json:"failures"`
}

// strategyCache persists the last working strategy to disk.
type strategyCache struct {
	LastWorkingStrategy string    `json:"last_working_strategy"`
	LastSuccess         time.Time `json:"last_success"`
}

// Extractor orchestrates multiple extraction strategies.
type Extractor struct {
	strategies     []Strategy
	lastWorking    string
	cacheDir       string
	stats          map[string]*strategyStats
}

// New creates an Extractor with the default strategy set.
func New(cacheDir string) *Extractor {
	e := &Extractor{
		strategies: []Strategy{
			NewDirectURLStrategy(),
			NewJSONWrapStrategy(),
			NewLegacyJSONStrategy(),
		},
		cacheDir: cacheDir,
		stats:    make(map[string]*strategyStats),
	}

	// Sort strategies by priority (lower = higher priority)
	sort.Slice(e.strategies, func(i, j int) bool {
		return e.strategies[i].Priority() < e.strategies[j].Priority()
	})

	// Initialize stats
	for _, s := range e.strategies {
		e.stats[s.Name()] = &strategyStats{}
	}

	// Load cached strategy
	e.loadCache()

	return e
}

// Extract tries strategies in order until one succeeds.
// It prioritizes the last working strategy for optimization.
func (e *Extractor) Extract(html string) (*StreamResult, error) {
	slog.Info("starting extraction", "strategies", len(e.strategies))

	// Quick validation
	if len(html) < 1000 {
		return nil, fmt.Errorf("HTML too small (%d bytes) — likely CAPTCHA or empty page", len(html))
	}

	// Try last working strategy first
	if e.lastWorking != "" {
		for _, s := range e.strategies {
			if s.Name() == e.lastWorking {
				slog.Info("trying cached strategy", "strategy", s.Name())
				if s.CanExtract(html) {
					result, err := s.Extract(html)
					if err == nil && result != nil {
						e.recordSuccess(s.Name())
						slog.Info("cached strategy succeeded", "strategy", s.Name())
						return result, nil
					}
				}
				break
			}
		}
	}

	// Try all strategies in priority order
	var lastErr error
	for _, s := range e.strategies {
		if s.Name() == e.lastWorking {
			continue // Already tried
		}

		slog.Info("trying strategy", "strategy", s.Name(), "priority", s.Priority())

		if !s.CanExtract(html) {
			slog.Debug("strategy pre-check failed", "strategy", s.Name())
			continue
		}

		result, err := s.Extract(html)
		if err != nil {
			e.recordFailure(s.Name())
			lastErr = fmt.Errorf("[%s] %w", s.Name(), err)
			slog.Debug("strategy failed", "strategy", s.Name(), "error", err)
			continue
		}

		if result != nil {
			e.recordSuccess(s.Name())
			e.lastWorking = s.Name()
			e.saveCache()
			slog.Info("extraction successful",
				"strategy", s.Name(),
				"title", result.Title,
				"qualities", len(result.Qualities),
			)
			return result, nil
		}
	}

	if lastErr != nil {
		return nil, fmt.Errorf("all strategies failed, last error: %w", lastErr)
	}
	return nil, fmt.Errorf("all strategies failed — no stream data found")
}

// IsCaptchaPage checks if the HTML is a CAPTCHA challenge page.
func IsCaptchaPage(html string) bool {
	return len(html) < 10000 && strings.Contains(html, "TTGCaptcha")
}

// Stats returns extraction statistics for all strategies.
func (e *Extractor) Stats() map[string]*strategyStats {
	return e.stats
}

func (e *Extractor) recordSuccess(name string) {
	if s, ok := e.stats[name]; ok {
		s.Successes++
	}
}

func (e *Extractor) recordFailure(name string) {
	if s, ok := e.stats[name]; ok {
		s.Failures++
	}
}

func (e *Extractor) cacheFilePath() string {
	if e.cacheDir == "" {
		return ""
	}
	return filepath.Join(e.cacheDir, ".strategy_cache.json")
}

func (e *Extractor) loadCache() {
	path := e.cacheFilePath()
	if path == "" {
		return
	}

	data, err := os.ReadFile(path)
	if err != nil {
		return
	}

	var cache strategyCache
	if err := json.Unmarshal(data, &cache); err != nil {
		return
	}

	e.lastWorking = cache.LastWorkingStrategy
	slog.Debug("loaded strategy cache", "strategy", e.lastWorking)
}

func (e *Extractor) saveCache() {
	path := e.cacheFilePath()
	if path == "" {
		return
	}

	// Ensure directory exists
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return
	}

	cache := strategyCache{
		LastWorkingStrategy: e.lastWorking,
		LastSuccess:         time.Now(),
	}

	data, err := json.Marshal(cache)
	if err != nil {
		return
	}

	_ = os.WriteFile(path, data, 0644)
	slog.Debug("saved strategy cache", "strategy", e.lastWorking)
}
