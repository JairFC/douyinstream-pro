// Package httpclient provides a pre-configured HTTP client for Douyin requests.
// It spoofs browser headers, handles redirects, and manages cookie injection.
package httpclient

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/http/cookiejar"
	"strings"
	"time"
)

const (
	// DefaultUserAgent mimics a real Chrome browser on Windows
	DefaultUserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

	// FirefoxUserAgent alternative — used by dylive project
	FirefoxUserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"

	// DefaultReferer for Douyin requests
	DefaultReferer = "https://www.douyin.com/"

	// DefaultTimeout for HTTP requests
	DefaultTimeout = 15 * time.Second
)

// Client wraps http.Client with Douyin-specific configuration.
type Client struct {
	http      *http.Client
	userAgent string
	referer   string
	cookies   map[string]string
}

// Option configures the Client.
type Option func(*Client)

// WithTimeout sets the HTTP client timeout.
func WithTimeout(d time.Duration) Option {
	return func(c *Client) {
		c.http.Timeout = d
	}
}

// WithUserAgent sets the User-Agent header.
func WithUserAgent(ua string) Option {
	return func(c *Client) {
		c.userAgent = ua
	}
}

// WithCookies sets cookies to include in requests.
func WithCookies(cookies map[string]string) Option {
	return func(c *Client) {
		for k, v := range cookies {
			c.cookies[k] = v
		}
	}
}

// New creates a new Douyin HTTP client with sensible defaults.
func New(opts ...Option) *Client {
	jar, _ := cookiejar.New(nil)

	c := &Client{
		http: &http.Client{
			Timeout: DefaultTimeout,
			Jar:     jar,
			// Don't follow redirects automatically — we handle them
			CheckRedirect: func(req *http.Request, via []*http.Request) error {
				if len(via) >= 10 {
					return fmt.Errorf("too many redirects")
				}
				return nil
			},
		},
		userAgent: DefaultUserAgent,
		referer:   DefaultReferer,
		cookies:   make(map[string]string),
	}

	for _, opt := range opts {
		opt(c)
	}

	return c
}

// Get performs a GET request with Douyin headers.
func (c *Client) Get(ctx context.Context, url string) (string, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return "", fmt.Errorf("creating request: %w", err)
	}

	c.applyHeaders(req)

	resp, err := c.http.Do(req)
	if err != nil {
		return "", fmt.Errorf("executing request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("reading response: %w", err)
	}

	return string(body), nil
}

// ResolveShortURL follows a v.douyin.com short URL to its final destination.
func (c *Client) ResolveShortURL(ctx context.Context, shortURL string) (string, error) {
	client := &http.Client{
		Timeout: c.http.Timeout,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			return http.ErrUseLastResponse
		},
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, shortURL, nil)
	if err != nil {
		return "", fmt.Errorf("creating request: %w", err)
	}
	req.Header.Set("User-Agent", c.userAgent)

	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("following redirect: %w", err)
	}
	defer resp.Body.Close()

	location := resp.Header.Get("Location")
	if location == "" {
		return shortURL, nil
	}

	return location, nil
}

// SetCookies adds or updates cookies for subsequent requests.
func (c *Client) SetCookies(cookies map[string]string) {
	for k, v := range cookies {
		c.cookies[k] = v
	}
}

// applyHeaders adds Douyin-specific headers to a request.
func (c *Client) applyHeaders(req *http.Request) {
	req.Header.Set("User-Agent", c.userAgent)
	req.Header.Set("Referer", c.referer)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8")
	req.Header.Set("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")

	// Build cookie string
	if len(c.cookies) > 0 {
		var parts []string
		for k, v := range c.cookies {
			parts = append(parts, fmt.Sprintf("%s=%s", k, v))
		}
		req.Header.Set("Cookie", strings.Join(parts, "; "))
	}
}
