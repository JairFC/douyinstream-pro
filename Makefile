# DouyinStream Go — Build System
# MIT License — github.com/JairFC/douyinstream-go

BINARY     := douyinstream
VERSION    ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
COMMIT     := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_TIME := $(shell date -u '+%Y-%m-%dT%H:%M:%SZ')

LDFLAGS := -s -w \
  -X main.version=$(VERSION) \
  -X main.commit=$(COMMIT) \
  -X main.buildTime=$(BUILD_TIME)

GOFLAGS := -trimpath

# ──────────────────────────────────────────────
# Development
# ──────────────────────────────────────────────

.PHONY: build
build: ## Build for current platform
	go build $(GOFLAGS) -ldflags "$(LDFLAGS)" -o bin/$(BINARY) ./cmd/douyinstream

.PHONY: run
run: build ## Build and run extract with a URL
	@echo "Usage: make run URL=https://live.douyin.com/XXXXX"
	@test -n "$(URL)" || (echo "ERROR: URL is required" && exit 1)
	./bin/$(BINARY) extract $(URL)

.PHONY: dev
dev: ## Build with race detector (development mode)
	go build -race $(GOFLAGS) -ldflags "$(LDFLAGS)" -o bin/$(BINARY) ./cmd/douyinstream

# ──────────────────────────────────────────────
# Quality
# ──────────────────────────────────────────────

.PHONY: test
test: ## Run all tests
	go test ./... -v -count=1

.PHONY: vet
vet: ## Run go vet
	go vet ./...

.PHONY: lint
lint: vet ## Run linting (go vet + staticcheck if available)
	@which staticcheck > /dev/null 2>&1 && staticcheck ./... || echo "staticcheck not installed — skipping"

.PHONY: check
check: vet test ## Run all checks (vet + tests)

# ──────────────────────────────────────────────
# Cross-compilation
# ──────────────────────────────────────────────

PLATFORMS := \
  linux-amd64 linux-arm64 \
  darwin-amd64 darwin-arm64 \
  windows-amd64

.PHONY: build-all
build-all: ## Cross-compile for all platforms
	@mkdir -p dist
	@for platform in $(PLATFORMS); do \
		GOOS=$${platform%%-*} GOARCH=$${platform##*-} \
		SUFFIX=""; \
		if [ "$${platform%%-*}" = "windows" ]; then SUFFIX=".exe"; fi; \
		echo "Building $${platform}..."; \
		GOOS=$${platform%%-*} GOARCH=$${platform##*-} \
		go build $(GOFLAGS) -ldflags "$(LDFLAGS)" \
			-o dist/$(BINARY)-$${platform}$${SUFFIX} \
			./cmd/douyinstream; \
	done
	@echo ""
	@echo "✅ Built all platforms:"
	@ls -lh dist/

.PHONY: build-linux
build-linux: ## Build for Linux amd64
	GOOS=linux GOARCH=amd64 go build $(GOFLAGS) -ldflags "$(LDFLAGS)" -o dist/$(BINARY)-linux-amd64 ./cmd/douyinstream

.PHONY: build-macos
build-macos: ## Build for macOS arm64 (Apple Silicon)
	GOOS=darwin GOARCH=arm64 go build $(GOFLAGS) -ldflags "$(LDFLAGS)" -o dist/$(BINARY)-darwin-arm64 ./cmd/douyinstream

.PHONY: build-windows
build-windows: ## Build for Windows amd64
	GOOS=windows GOARCH=amd64 go build $(GOFLAGS) -ldflags "$(LDFLAGS)" -o dist/$(BINARY)-windows-amd64.exe ./cmd/douyinstream

# ──────────────────────────────────────────────
# Release
# ──────────────────────────────────────────────

.PHONY: release
release: clean build-all ## Build release artifacts with checksums
	@cd dist && sha256sum * > checksums.sha256
	@echo ""
	@cat dist/checksums.sha256
	@echo ""
	@echo "🚀 Release artifacts ready in dist/"

.PHONY: tag
tag: ## Create a version tag (usage: make tag V=v2.0.0-beta.2)
	@test -n "$(V)" || (echo "ERROR: specify version with V=v2.0.0-beta.X" && exit 1)
	@echo "Creating tag $(V)..."
	git tag -a $(V) -m "$(V)"
	@echo "Push with: git push origin v2-go --tags"

.PHONY: release-github
release-github: ## Create GitHub release via goreleaser (requires tag)
	@which goreleaser > /dev/null 2>&1 || (echo "Install goreleaser: go install github.com/goreleaser/goreleaser/v2@latest" && exit 1)
	goreleaser release --clean

# ──────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────

.PHONY: clean
clean: ## Remove build artifacts
	rm -rf bin/ dist/

.PHONY: deps
deps: ## Download and tidy dependencies
	go mod download
	go mod tidy

# ──────────────────────────────────────────────
# Info
# ──────────────────────────────────────────────

.PHONY: version
version: ## Show version info
	@echo "Version:    $(VERSION)"
	@echo "Commit:     $(COMMIT)"
	@echo "Build Time: $(BUILD_TIME)"
	@echo "Branch:     $$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'N/A')"
	@echo "Tags:       $$(git tag -l 'v*' --sort=-version:refname 2>/dev/null | head -5 | tr '\n' ' ' || echo 'none')"

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

