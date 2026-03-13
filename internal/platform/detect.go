// Package platform detects streaming platforms from URLs.
package platform

import (
	"net/url"
	"regexp"
	"strings"
)

// Platform represents a supported streaming platform.
type Platform string

const (
	PlatformDouyin   Platform = "douyin"
	PlatformTikTok   Platform = "tiktok"
	PlatformUnknown  Platform = "unknown"
)

// platformPattern maps regex patterns to platforms.
type platformPattern struct {
	Platform Platform
	Patterns []*regexp.Regexp
}

var platformPatterns = []platformPattern{
	{
		Platform: PlatformDouyin,
		Patterns: []*regexp.Regexp{
			regexp.MustCompile(`(?i)live\.douyin\.com`),
			regexp.MustCompile(`(?i)v\.douyin\.com`),
			regexp.MustCompile(`(?i)www\.douyin\.com/root/live`),
			regexp.MustCompile(`(?i)webcast\.amemv\.com`),
		},
	},
	{
		Platform: PlatformTikTok,
		Patterns: []*regexp.Regexp{
			regexp.MustCompile(`(?i)tiktok\.com/@[^/]+/live`),
			regexp.MustCompile(`(?i)vm\.tiktok\.com`),
		},
	},
}

// Detect identifies the platform from a URL string.
func Detect(rawURL string) Platform {
	for _, pp := range platformPatterns {
		for _, re := range pp.Patterns {
			if re.MatchString(rawURL) {
				return pp.Platform
			}
		}
	}
	return PlatformUnknown
}

// IsDouyin returns true if the URL is a Douyin URL.
func IsDouyin(rawURL string) bool {
	return Detect(rawURL) == PlatformDouyin
}

// IsShortURL checks if the URL is a short redirect URL (v.douyin.com).
func IsShortURL(rawURL string) bool {
	return strings.Contains(rawURL, "v.douyin.com")
}

// ExtractRoomID tries to extract the room ID from a Douyin live URL.
// e.g., "https://live.douyin.com/94782239787" → "94782239787"
func ExtractRoomID(rawURL string) string {
	u, err := url.Parse(rawURL)
	if err != nil {
		return ""
	}

	path := strings.TrimRight(u.Path, "/")
	parts := strings.Split(path, "/")
	if len(parts) > 0 {
		lastPart := parts[len(parts)-1]
		// Room IDs are numeric
		if matched, _ := regexp.MatchString(`^\d+$`, lastPart); matched {
			return lastPart
		}
	}

	return ""
}

// NormalizeLiveURL ensures the URL is in the standard live.douyin.com format.
func NormalizeLiveURL(rawURL string) string {
	roomID := ExtractRoomID(rawURL)
	if roomID != "" {
		return "https://live.douyin.com/" + roomID
	}
	return rawURL
}
