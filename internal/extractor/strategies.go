package extractor

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"regexp"
	"strings"
)

// --------------------------------------------------------------------------
// Strategy 1: DirectURLStrategy — Regex for .flv/.m3u8 URLs in HTML
// Most robust — doesn't depend on JSON structure.
// --------------------------------------------------------------------------

type directURLStrategy struct{}

func NewDirectURLStrategy() Strategy {
	return &directURLStrategy{}
}

func (s *directURLStrategy) Name() string     { return "DirectURL" }
func (s *directURLStrategy) Priority() int    { return 1 }

var (
	flvPattern  = regexp.MustCompile(`"(https?://[^"]+\.flv[^"]*)"`)
	m3u8Pattern = regexp.MustCompile(`"(https?://[^"]+\.m3u8[^"]*)"`)
	qualityPattern = regexp.MustCompile(`_(sd|hd|uhd|origin|ld)\.`)
	titlePattern   = regexp.MustCompile(`"title":"([^"]+)"`)
	authorPattern  = regexp.MustCompile(`"nickname":"([^"]+)"`)
)

func (s *directURLStrategy) CanExtract(html string) bool {
	return flvPattern.MatchString(html) || m3u8Pattern.MatchString(html)
}

func (s *directURLStrategy) Extract(html string) (*StreamResult, error) {
	flvURLs := flvPattern.FindAllStringSubmatch(html, 20)
	m3u8URLs := m3u8Pattern.FindAllStringSubmatch(html, 20)

	if len(flvURLs) == 0 && len(m3u8URLs) == 0 {
		return nil, fmt.Errorf("no FLV or M3U8 URLs found in HTML")
	}

	// Collect all URLs
	var allURLs []string
	for _, m := range flvURLs {
		allURLs = append(allURLs, m[1])
	}
	for _, m := range m3u8URLs {
		allURLs = append(allURLs, m[1])
	}

	// Prefer FLV over M3U8 for best quality
	bestURL := allURLs[0]

	// Map quality variants
	qualities := make(map[string]string)
	for _, url := range allURLs {
		qm := qualityPattern.FindStringSubmatch(url)
		if qm != nil {
			quality := qm[1]
			if _, exists := qualities[quality]; !exists {
				qualities[quality] = url
			}
		}
	}

	if len(qualities) == 0 {
		qualities["best"] = bestURL
	}

	// Extract metadata
	title := "Douyin Live"
	author := "Unknown"

	if m := titlePattern.FindStringSubmatch(html); m != nil {
		title = m[1]
	}
	if m := authorPattern.FindStringSubmatch(html); m != nil {
		author = m[1]
	}

	return &StreamResult{
		URL:       bestURL,
		Title:     title,
		Author:    author,
		IsLive:    true,
		Qualities: qualities,
	}, nil
}

// --------------------------------------------------------------------------
// Strategy 2: JSONWrapStrategy — Parse __pace_f.push() → streamStore
// Handles the current format used by Douyin.
// Adapted from dylive's getDataInHtml() and Python reference.
// --------------------------------------------------------------------------

type jsonWrapStrategy struct{}

func NewJSONWrapStrategy() Strategy {
	return &jsonWrapStrategy{}
}

func (s *jsonWrapStrategy) Name() string     { return "JSONWrap" }
func (s *jsonWrapStrategy) Priority() int    { return 2 }

func (s *jsonWrapStrategy) CanExtract(html string) bool {
	return strings.Contains(html, "__pace_f") && strings.Contains(html, "streamStore")
}

func (s *jsonWrapStrategy) Extract(html string) (*StreamResult, error) {
	// Parse __pace_f blocks from HTML (adapted from dylive's getDataInHtml)
	parts := parsePaceData(html)

	// Collect ALL parts containing streamStore or roomStore
	// Try them all — prefer smaller, more specific parts (which contain "state" directly)
	type candidate struct {
		part string
		size int
	}
	var candidates []candidate

	for _, part := range parts {
		if strings.Contains(part, "streamStore") || strings.Contains(part, "flv_pull_url") || strings.Contains(part, "roomStore") {
			candidates = append(candidates, candidate{part: part, size: len(part)})
		}
	}

	if len(candidates) == 0 {
		return nil, fmt.Errorf("no streamStore/roomStore found in __pace_f data")
	}

	// Sort by size ascending — prefer the smaller, more specific blocks
	// (the larger ones are Next.js full state dumps with different key structure)
	for i := 0; i < len(candidates)-1; i++ {
		for j := i + 1; j < len(candidates); j++ {
			if candidates[j].size < candidates[i].size {
				candidates[i], candidates[j] = candidates[j], candidates[i]
			}
		}
	}

	// Try each candidate until one succeeds
	var lastErr error
	for _, c := range candidates {
		result, err := parseRoomData(c.part)
		if err == nil && result != nil {
			return result, nil
		}
		lastErr = err
		slog.Debug("JSONWrap candidate failed", "size", c.size, "error", err)
	}

	if lastErr != nil {
		return nil, fmt.Errorf("all JSONWrap candidates failed: %w", lastErr)
	}
	return nil, fmt.Errorf("no streamStore found in __pace_f data")
}

// --------------------------------------------------------------------------
// Strategy 3: LegacyJSONStrategy — Fallback for older JSON format
// Uses same __pace_f parsing but tries different JSON navigation.
// --------------------------------------------------------------------------

type legacyJSONStrategy struct{}

func NewLegacyJSONStrategy() Strategy {
	return &legacyJSONStrategy{}
}

func (s *legacyJSONStrategy) Name() string     { return "LegacyJSON" }
func (s *legacyJSONStrategy) Priority() int    { return 3 }

func (s *legacyJSONStrategy) CanExtract(html string) bool {
	return strings.Contains(html, "__pace_f")
}

func (s *legacyJSONStrategy) Extract(html string) (*StreamResult, error) {
	parts := parsePaceData(html)

	// Try each part that might contain room data, in any order
	var lastErr error
	for _, part := range parts {
		if !strings.Contains(part, "roomStore") && !strings.Contains(part, "flv_pull_url") {
			continue
		}

		result, err := parseRoomData(part)
		if err == nil && result != nil {
			return result, nil
		}
		lastErr = err
	}

	if lastErr != nil {
		return nil, fmt.Errorf("legacy parsing failed: %w", lastErr)
	}
	return nil, fmt.Errorf("no valid room data found in __pace_f blocks")
}

// --------------------------------------------------------------------------
// Shared parsing utilities
// --------------------------------------------------------------------------

// parsePaceData extracts JSON blocks from __pace_f.push() calls in HTML.
// Adapted from dylive's getDataInHtml() function (MIT licensed).
func parsePaceData(html string) []string {
	const funcName = "__pace_f"
	const endTag = "</script>"

	var parts []string
	input := html

	for {
		a := strings.Index(input, funcName)
		if a == -1 {
			break
		}
		input = input[a+len(funcName):]

		// Find the opening quote
		b := strings.Index(input, `"`)
		if b < 0 {
			continue
		}
		input = input[b+1:]

		// Find the closing tag
		endIdx := strings.Index(input, endTag)
		if endIdx < 0 {
			continue
		}

		// Find the last quote before the end tag
		lastQuote := strings.LastIndex(input[:endIdx], `"`)
		if lastQuote < 0 {
			continue
		}

		// Unescape the JSON string
		rawJSON := input[:lastQuote]
		var unescaped string
		if err := json.Unmarshal([]byte(`"`+rawJSON+`"`), &unescaped); err != nil {
			continue
		}

		parts = append(parts, unescaped)
	}

	// Split by newlines and extract JSON objects/arrays
	var result []string
	allParts := strings.Split(strings.Join(parts, "\n"), "\n")

	for _, part := range allParts {
		a := strings.IndexAny(part, "[{")
		if a == -1 {
			continue
		}
		b := strings.LastIndexAny(part, "}]")
		if b == -1 || b < a {
			continue
		}
		result = append(result, part[a:b+1])
	}

	return result
}

// roomData represents the JSON structure embedded in Douyin pages.
type roomData struct {
	State struct {
		RoomStore struct {
			RoomInfo struct {
				Room   roomInfo `json:"room"`
				WebRid string   `json:"web_rid"`
				Anchor struct {
					Nickname string `json:"nickname"`
				} `json:"anchor"`
			} `json:"roomInfo"`
		} `json:"roomStore"`
		StreamStore struct {
			StreamData struct {
				H264    codecStreamData `json:"H264_streamData"`
				H265    codecStreamData `json:"H265_streamData"`
				H264UGC codecStreamData `json:"UGC_streamData"`
				H265UGC codecStreamData `json:"H265_UGC_streamData"`
			} `json:"streamData"`
		} `json:"streamStore"`
	} `json:"state"`
}

type codecStreamData struct {
	Stream map[string]streamQuality `json:"stream"`
}

type roomInfo struct {
	IDStr  string `json:"id_str"`
	Title  string `json:"title"`
	Status int    `json:"status"`
	Owner  struct {
		Nickname string `json:"nickname"`
	} `json:"owner"`
	StreamURL struct {
		FlvPullURL        map[string]string `json:"flv_pull_url"`
		HlsPullURLMap     map[string]string `json:"hls_pull_url_map"`
		DefaultResolution string            `json:"default_resolution"`
		Extra             struct {
			Height int `json:"height"`
			Width  int `json:"width"`
			FPS    int `json:"fps"`
		} `json:"extra"`
		LiveCoreSDKData json.RawMessage `json:"live_core_sdk_data"`
	} `json:"stream_url"`
}

type streamQuality struct {
	Main struct {
		FLV       string `json:"flv"`
		HLS       string `json:"hls"`
		SDKParams string `json:"sdk_params"`
	} `json:"main"`
}

// sdkParams holds the resolution/codec/bitrate info from sdk_params JSON string.
type sdkParams struct {
	VWidth  int    `json:"vwidth"`
	VHeight int    `json:"vheight"`
	FPS     int    `json:"fps"`
	VBitrate int   `json:"vbitrate"`
	VCodec  string `json:"VCodec"`
}

// parseRoomData extracts stream URLs from a JSON block.
func parseRoomData(jsonStr string) (*StreamResult, error) {
	// Try to parse as a JSON array first (wrapper format)
	var array []json.RawMessage
	if err := json.Unmarshal([]byte(jsonStr), &array); err != nil {
		// Not an array — try direct parsing
		return parseRoomDataDirect(jsonStr)
	}

	// Look for an object with "state" or relevant keys in the array
	for _, element := range array {
		var obj map[string]json.RawMessage
		if err := json.Unmarshal(element, &obj); err != nil {
			continue
		}

		// Primary format: { "state": { "roomStore": ... } }
		if _, hasState := obj["state"]; hasState {
			result, err := parseRoomDataDirect(string(element))
			if err == nil && result != nil {
				return result, nil
			}
		}

		// Alternative format: { "initialState": { "roomStore": ... } }
		if initialState, ok := obj["initialState"]; ok {
			wrapped := fmt.Sprintf(`{"state":%s}`, string(initialState))
			result, err := parseRoomDataDirect(wrapped)
			if err == nil && result != nil {
				return result, nil
			}
		}

		// Direct format: { "roomStore": ..., "streamStore": ... }
		if _, hasRS := obj["roomStore"]; hasRS {
			wrapped := fmt.Sprintf(`{"state":%s}`, string(element))
			result, err := parseRoomDataDirect(wrapped)
			if err == nil && result != nil {
				return result, nil
			}
		}
	}

	return nil, fmt.Errorf("no state/roomStore found in JSON array")
}

// parseRoomDataDirect parses a JSON object containing room/stream data.
func parseRoomDataDirect(jsonStr string) (*StreamResult, error) {
	var data roomData
	if err := json.Unmarshal([]byte(jsonStr), &data); err != nil {
		return nil, fmt.Errorf("JSON parse error: %w", err)
	}

	room := data.State.RoomStore.RoomInfo
	isLive := room.Room.Status == 2

	title := room.Room.Title
	if title == "" {
		title = "Douyin Live"
	}

	author := room.Anchor.Nickname
	if author == "" {
		author = room.Room.Owner.Nickname
	}
	if author == "" {
		author = "Unknown"
	}

	qualities := make(map[string]string)
	qualityMeta := make(map[string]QualityMeta)
	var bestURL string

	// ─── Method 1: streamStore H264 + H265 (RICHEST DATA) ───
	// This gives us all quality tiers including "origin" with full
	// resolution/fps/bitrate metadata from sdk_params.
	extractCodecStreams := func(codecData codecStreamData, codec string) {
		for qName, qData := range codecData.Stream {
			if qData.Main.FLV == "" {
				continue
			}

			// Build key: e.g. "origin_h265_flv", "uhd_h264_flv"
			keyFLV := fmt.Sprintf("%s_%s_flv", qName, codec)
			qualities[keyFLV] = qData.Main.FLV

			if qData.Main.HLS != "" {
				keyHLS := fmt.Sprintf("%s_%s_hls", qName, codec)
				qualities[keyHLS] = qData.Main.HLS
			}

			// Parse sdk_params for resolution/fps/bitrate
			var params sdkParams
			if qData.Main.SDKParams != "" {
				_ = json.Unmarshal([]byte(qData.Main.SDKParams), &params)
			}

			meta := QualityMeta{
				Width:   params.VWidth,
				Height:  params.VHeight,
				FPS:     params.FPS,
				Bitrate: params.VBitrate,
				Codec:   codec,
			}
			qualityMeta[keyFLV] = meta
			if qData.Main.HLS != "" {
				keyHLS := fmt.Sprintf("%s_%s_hls", qName, codec)
				qualityMeta[keyHLS] = meta
			}
		}
	}

	extractCodecStreams(data.State.StreamStore.StreamData.H265, "h265")
	extractCodecStreams(data.State.StreamStore.StreamData.H264, "h264")

	if len(qualities) > 0 {
		slog.Info("extracted via streamStore",
			"h264_qualities", len(data.State.StreamStore.StreamData.H264.Stream),
			"h265_qualities", len(data.State.StreamStore.StreamData.H265.Stream),
		)
	}

	// ─── Method 2: flv_pull_url / hls_pull_url_map (SIMPLE) ───
	// Fallback if streamStore is empty. Only has H264 without metadata.
	if len(qualities) == 0 && len(room.Room.StreamURL.FlvPullURL) > 0 {
		for key, url := range room.Room.StreamURL.FlvPullURL {
			qualities[key] = url
		}
		for key, url := range room.Room.StreamURL.HlsPullURLMap {
			qualities[key+"_hls"] = url
		}
		slog.Info("extracted via flv_pull_url",
			"qualities", len(room.Room.StreamURL.FlvPullURL),
		)
	}

	// ─── Select best URL ───
	// Priority: origin_h265 > origin_h264 > uhd_h265 > uhd_h264 > FULL_HD1 > ...
	bestPriority := []string{
		"origin_h265_flv",
		"origin_h264_flv",
		"uhd_h265_flv",
		"uhd_h264_flv",
		"FULL_HD1",
		"hd_h265_flv",
		"hd_h264_flv",
		"HD1",
	}
	for _, key := range bestPriority {
		if url, ok := qualities[key]; ok {
			bestURL = url
			break
		}
	}
	if bestURL == "" {
		for _, url := range qualities {
			bestURL = url
			break
		}
	}

	if bestURL == "" {
		if title != "Douyin Live" || room.Room.IDStr != "" {
			slog.Info("room found but no active stream",
				"title", title,
				"author", author,
				"status", room.Room.Status,
			)
			return &StreamResult{
				Title:     title,
				Author:    author,
				IsLive:    false,
				RoomID:    room.Room.IDStr,
				Qualities: qualities,
			}, nil
		}
		return nil, fmt.Errorf("no stream URLs found in room data")
	}

	return &StreamResult{
		URL:          bestURL,
		Title:        title,
		Author:       author,
		IsLive:       isLive,
		Qualities:    qualities,
		QualityMeta:  qualityMeta,
		RoomID:       room.Room.IDStr,
	}, nil
}

