// Package cookie manages cookie acquisition for Douyin requests.
// It supports dynamic generation, browser extraction, and file-based loading.
package cookie

import (
	"context"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"regexp"
	"strings"
)

// Cookies represents a collection of cookies needed for Douyin requests.
type Cookies struct {
	MSToken              string `json:"ms_token,omitempty"`
	TTwid                string `json:"ttwid,omitempty"`
	AcNonce              string `json:"ac_nonce,omitempty"`
	OdinTT               string `json:"odin_tt,omitempty"`
	BDTicketGuardClient  string `json:"bd_ticket_guard_client_data,omitempty"`
}

// ToMap converts cookies to a string map for HTTP headers.
func (c *Cookies) ToMap() map[string]string {
	m := make(map[string]string)
	if c.MSToken != "" {
		m["msToken"] = c.MSToken
	}
	if c.TTwid != "" {
		m["ttwid"] = c.TTwid
	}
	if c.AcNonce != "" {
		m["__ac_nonce"] = c.AcNonce
	}
	if c.OdinTT != "" {
		m["odin_tt"] = c.OdinTT
	}
	if c.BDTicketGuardClient != "" {
		m["bd_ticket_guard_client_data"] = c.BDTicketGuardClient
	}
	return m
}

// Merge combines cookies from another set, overwriting existing values.
func (c *Cookies) Merge(other *Cookies) {
	if other.MSToken != "" {
		c.MSToken = other.MSToken
	}
	if other.TTwid != "" {
		c.TTwid = other.TTwid
	}
	if other.AcNonce != "" {
		c.AcNonce = other.AcNonce
	}
	if other.OdinTT != "" {
		c.OdinTT = other.OdinTT
	}
	if other.BDTicketGuardClient != "" {
		c.BDTicketGuardClient = other.BDTicketGuardClient
	}
}

// GenerateDynamic creates fresh cookies without browser access.
// Adapted from lux's douyin extractor (MIT licensed).
// This is the preferred method — no login, no browser, no CAPTCHA.
func GenerateDynamic(ctx context.Context) (*Cookies, error) {
	slog.Info("generating dynamic cookies")

	cookies := &Cookies{}

	// 1. Generate msToken (random 107-char alphanumeric)
	msToken, err := generateMSToken(107)
	if err != nil {
		return nil, fmt.Errorf("generating msToken: %w", err)
	}
	cookies.MSToken = msToken
	slog.Debug("generated msToken", "length", len(msToken))

	// 2. Get ttwid from ByteDance registration endpoint
	ttwid, err := fetchTTwid(ctx)
	if err != nil {
		slog.Warn("failed to get ttwid, continuing without it", "error", err)
	} else {
		cookies.TTwid = ttwid
		slog.Debug("obtained ttwid", "length", len(ttwid))
	}

	// 3. Set known static values
	cookies.AcNonce = "064caded4009deafd8b89" // Used by dylive
	cookies.OdinTT = "324fb4ea4a89c0c05827e18a1ed9cf9bf8a17f7705fcc793fec935b637867e2a5a9b8168c885554d029919117a18ba69"

	slog.Info("dynamic cookies generated successfully")
	return cookies, nil
}

// generateMSToken generates a random alphanumeric token of the given length.
// Adapted from lux's msToken() function.
func generateMSToken(length int) (string, error) {
	const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

	randomBytes := make([]byte, length)
	if _, err := rand.Read(randomBytes); err != nil {
		return "", err
	}

	token := make([]byte, length)
	for i, b := range randomBytes {
		token[i] = chars[int(b)%len(chars)]
	}

	return string(token), nil
}

// fetchTTwid obtains a ttwid cookie from ByteDance's registration endpoint.
// Adapted from lux's ttwid() function.
func fetchTTwid(ctx context.Context) (string, error) {
	body := map[string]interface{}{
		"aid":           1768,
		"union":         true,
		"needFid":       false,
		"region":        "cn",
		"cbUrlProtocol": "https",
		"service":       "www.ixigua.com",
		"migrate_info":  map[string]string{"ticket": "", "source": "node"},
	}

	jsonBody, err := json.Marshal(body)
	if err != nil {
		return "", err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		"https://ttwid.bytedance.com/ttwid/union/register/",
		strings.NewReader(string(jsonBody)),
	)
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	// Extract ttwid from Set-Cookie header
	cookieHeader := resp.Header.Get("Set-Cookie")
	re := regexp.MustCompile(`ttwid=([^;]+)`)
	match := re.FindStringSubmatch(cookieHeader)
	if match == nil {
		return "", fmt.Errorf("ttwid not found in response cookies")
	}

	return match[1], nil
}

// LoadFromMap creates Cookies from a string map (e.g., from config file).
func LoadFromMap(m map[string]string) *Cookies {
	return &Cookies{
		MSToken:             m["msToken"],
		TTwid:               m["ttwid"],
		AcNonce:             m["__ac_nonce"],
		OdinTT:              m["odin_tt"],
		BDTicketGuardClient: m["bd_ticket_guard_client_data"],
	}
}
