/**
 * DouyinStream Pro v2 - Frontend Application
 * Vanilla JavaScript for API integration and player control.
 */

// API Configuration
const API_BASE = 'http://127.0.0.1:8000';
const WS_URL = 'ws://127.0.0.1:8000/ws/logs';

// State
let currentStream = null;
let isGamingMode = false;
let wsConnection = null;
let favorites = [];

// DOM Elements
const elements = {
    urlInput: null,
    playBtn: null,
    stopBtn: null,
    videoPlayer: null,
    playerPlaceholder: null,
    streamInfo: null,
    streamTitle: null,
    streamAuthor: null,
    favoritesList: null,
    consoleOutput: null,
    statusDot: null,
    statusText: null,
    captchaModal: null,
    qualitySelect: null,
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    initElements();
    initWebSocket();
    loadFavorites();
    checkSystemStatus();
    setupClipboardWatch();
    log('Application initialized', 'success');
});

function initElements() {
    elements.urlInput = document.getElementById('url-input');
    elements.playBtn = document.getElementById('play-btn');
    elements.stopBtn = document.getElementById('stop-btn');
    elements.videoPlayer = document.getElementById('video-player');
    elements.playerPlaceholder = document.getElementById('player-placeholder');
    elements.streamInfo = document.getElementById('stream-info');
    elements.streamTitle = document.getElementById('stream-title');
    elements.streamAuthor = document.getElementById('stream-author');
    elements.favoritesList = document.getElementById('favorites-list');
    elements.consoleOutput = document.getElementById('console-output');
    elements.statusDot = document.querySelector('.status-dot');
    elements.statusText = document.querySelector('.status-text');
    elements.captchaModal = document.getElementById('captcha-modal');
    elements.qualitySelect = document.getElementById('quality-select');

    // Enter key to play
    elements.urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') playStream();
    });
}

// WebSocket for real-time logs
function initWebSocket() {
    try {
        wsConnection = new WebSocket(WS_URL);

        wsConnection.onopen = () => {
            updateStatus('online', 'Connected');
            log('WebSocket connected', 'success');
        };

        wsConnection.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleWsMessage(data);
        };

        wsConnection.onclose = () => {
            updateStatus('offline', 'Disconnected');
            log('WebSocket disconnected, reconnecting...', 'warning');
            setTimeout(initWebSocket, 3000);
        };

        wsConnection.onerror = (error) => {
            updateStatus('error', 'Connection Error');
            log('WebSocket error', 'error');
        };
    } catch (e) {
        log('Failed to connect WebSocket: ' + e.message, 'error');
    }
}

function handleWsMessage(data) {
    switch (data.type) {
        case 'log':
            log(`[${data.data.source}] ${data.data.message}`, data.data.level.toLowerCase());
            break;
        case 'status':
            handleStreamStatus(data.data);
            break;
        case 'stream_event':
            handleStreamEvent(data);
            break;
    }
}

function handleStreamStatus(data) {
    // Update favorite status indicator
    const favItem = document.querySelector(`[data-url="${data.url}"]`);
    if (favItem) {
        const statusDot = favItem.querySelector('.favorite-status');
        statusDot.className = 'favorite-status ' + (data.status === 'live' ? 'live' : 'offline');
    }
}

function handleStreamEvent(data) {
    if (data.event === 'status_change' && data.data.is_live) {
        showToast(`🟢 ${data.data.title || 'Stream'} is now LIVE!`, 'success');
    }
}

// Stream Control
async function playStream(url = null) {
    const targetUrl = url || elements.urlInput.value.trim();

    if (!targetUrl) {
        showToast('Please enter a URL', 'warning');
        return;
    }

    log(`Extracting stream: ${targetUrl}`);
    elements.playBtn.disabled = true;
    elements.playBtn.textContent = '⌛ Loading...';

    try {
        const response = await fetch(`${API_BASE}/api/streams/extract`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: targetUrl,
                quality: elements.qualitySelect.value
            })
        });

        if (response.status === 403) {
            const error = await response.json();
            if (error.detail?.error === 'captcha_required') {
                showCaptchaModal();
                return;
            }
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to extract stream');
        }

        const data = await response.json();

        if (!data.stream_url) {
            throw new Error('No stream URL found - stream may be offline');
        }

        currentStream = data;
        startPlayer(data);
        updateStreamInfo(data);

        // Mark as played
        fetch(`${API_BASE}/api/favorites/${encodeURIComponent(targetUrl)}/played`, {
            method: 'POST'
        });

        log(`Playing: ${data.title}`, 'success');
        showToast('Stream started!', 'success');

    } catch (error) {
        log(`Error: ${error.message}`, 'error');
        showToast(error.message, 'error');
    } finally {
        elements.playBtn.disabled = false;
        elements.playBtn.textContent = '▶ Play';
    }
}

function startPlayer(streamData) {
    const player = elements.videoPlayer;
    const placeholder = elements.playerPlaceholder;

    // Show video player, hide placeholder
    placeholder.classList.add('hidden');
    player.classList.remove('hidden');

    // Set source and play
    player.src = streamData.stream_url;
    player.play().catch(e => log('Autoplay blocked: ' + e.message, 'warning'));

    // Show/hide buttons
    elements.playBtn.classList.add('hidden');
    elements.stopBtn.classList.remove('hidden');

    // Handle stream end
    player.onended = () => {
        log('Stream ended', 'info');
        handleStreamEnd();
    };

    player.onerror = () => {
        log('Playback error', 'error');
        showToast('Playback error - stream may have ended', 'error');
    };
}

function stopStream() {
    const player = elements.videoPlayer;

    player.pause();
    player.src = '';
    player.classList.add('hidden');
    elements.playerPlaceholder.classList.remove('hidden');

    elements.stopBtn.classList.add('hidden');
    elements.playBtn.classList.remove('hidden');
    elements.streamInfo.classList.add('hidden');

    currentStream = null;
    log('Stream stopped');
}

async function handleStreamEnd() {
    log('Checking for next live stream...');

    // Find next live favorite
    const liveFavorite = favorites.find(f => f.is_live);
    if (liveFavorite) {
        log(`Auto-switching to: ${liveFavorite.alias || liveFavorite.url}`);
        showToast('Switching to next live stream...', 'info');
        await playStream(liveFavorite.url);
    } else {
        stopStream();
        showToast('Stream ended. No other live streams found.', 'info');
    }
}

function updateStreamInfo(data) {
    elements.streamTitle.textContent = data.title || 'Unknown Stream';
    elements.streamAuthor.textContent = `by ${data.author || 'Unknown'}`;
    elements.streamInfo.classList.remove('hidden');
}

// Favorites
async function loadFavorites() {
    try {
        const response = await fetch(`${API_BASE}/api/favorites`);
        if (!response.ok) throw new Error('Failed to load favorites');

        const data = await response.json();
        favorites = data.favorites || [];
        renderFavorites();
    } catch (error) {
        elements.favoritesList.innerHTML = '<div class="loading-text">Could not load favorites</div>';
        log('Failed to load favorites: ' + error.message, 'error');
    }
}

function renderFavorites() {
    if (favorites.length === 0) {
        elements.favoritesList.innerHTML = '<div class="loading-text">No favorites yet</div>';
        return;
    }

    elements.favoritesList.innerHTML = favorites.map(fav => `
        <div class="favorite-item" data-url="${fav.url}" onclick="playStream('${fav.url}')">
            <span class="favorite-status ${fav.is_live ? 'live' : ''}"></span>
            <div class="favorite-info">
                <div class="favorite-name">${fav.alias || extractRoomId(fav.url)}</div>
                <div class="favorite-url">${fav.url.substring(0, 30)}...</div>
            </div>
            <button class="favorite-delete" onclick="event.stopPropagation(); deleteFavorite('${fav.url}')">✕</button>
        </div>
    `).join('');
}

function extractRoomId(url) {
    const match = url.match(/\/(\d+)/);
    return match ? `Room ${match[1]}` : 'Unknown';
}

async function addCurrentToFavorites() {
    const url = elements.urlInput.value.trim() || currentStream?.url;
    if (!url) {
        showToast('No URL to add', 'warning');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/favorites`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, alias: currentStream?.title || '' })
        });

        if (response.status === 409) {
            showToast('Already in favorites', 'info');
            return;
        }

        if (!response.ok) throw new Error('Failed to add favorite');

        showToast('Added to favorites!', 'success');
        loadFavorites();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function deleteFavorite(url) {
    try {
        await fetch(`${API_BASE}/api/favorites/${encodeURIComponent(url)}`, {
            method: 'DELETE'
        });
        loadFavorites();
        showToast('Removed from favorites', 'info');
    } catch (error) {
        showToast('Failed to delete', 'error');
    }
}

async function checkAllLive() {
    log('Checking all favorites for live status...');
    showToast('Checking live status...', 'info');

    // Trigger backend check
    try {
        const response = await fetch(`${API_BASE}/api/favorites/live/all`);
        const data = await response.json();
        log(`Found ${data.live_count || 0} live streams`);
    } catch (error) {
        log('Error checking live status', 'error');
    }
}

// Gaming Mode
async function toggleGamingMode() {
    const btn = document.getElementById('gaming-mode-btn');

    if (isGamingMode) {
        // Resume
        try {
            await fetch(`${API_BASE}/api/system/resume`, { method: 'POST' });
            isGamingMode = false;
            btn.textContent = '🎮 Gaming Mode';
            btn.classList.remove('active');
            showToast('Background tasks resumed', 'success');
            log('Gaming mode disabled');
        } catch (error) {
            showToast('Failed to resume', 'error');
        }
    } else {
        // Pause
        try {
            await fetch(`${API_BASE}/api/system/pause`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason: 'gaming' })
            });
            isGamingMode = true;
            btn.textContent = '▶ Resume';
            btn.style.background = 'var(--warning)';
            showToast('Background tasks paused for gaming', 'success');
            log('Gaming mode enabled - background tasks paused');
        } catch (error) {
            showToast('Failed to pause', 'error');
        }
    }
}

// CAPTCHA handling
function showCaptchaModal() {
    elements.captchaModal.classList.remove('hidden');
}

function closeCaptchaModal() {
    elements.captchaModal.classList.add('hidden');
}

async function refreshCookies() {
    log('Refreshing cookies from browser...');
    showToast('Refreshing cookies...', 'info');

    try {
        const response = await fetch(`${API_BASE}/api/streams/refresh-cookies`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            showToast(`Cookies refreshed: ${data.cookies_count} found`, 'success');
            closeCaptchaModal();
        } else {
            showToast(data.message || 'No cookies found', 'warning');
        }
    } catch (error) {
        showToast('Failed to refresh cookies', 'error');
    }
}

// System status
async function checkSystemStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/system/status`);
        const data = await response.json();

        updateStatus(data.status === 'running' ? 'online' : 'paused',
            data.status === 'running' ? 'Connected' : 'Paused');

        if (!data.cookies_valid) {
            log('Warning: No valid Douyin cookies found', 'warning');
        }
    } catch (error) {
        updateStatus('error', 'Backend Offline');
        log('Cannot connect to backend', 'error');
    }
}

// Clipboard watching
function setupClipboardWatch() {
    document.addEventListener('paste', (e) => {
        const text = e.clipboardData?.getData('text') || '';
        if (text.includes('douyin.com') || text.includes('tiktok.com')) {
            elements.urlInput.value = text;
            showToast('URL detected! Click Play to start.', 'info');
        }
    });
}

// UI Helpers
function updateStatus(state, text) {
    elements.statusDot.className = 'status-dot ' + state;
    elements.statusText.textContent = text;
}

function log(message, level = 'info') {
    const entry = document.createElement('div');
    entry.className = `log-entry log-${level}`;
    entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    elements.consoleOutput.appendChild(entry);
    elements.consoleOutput.scrollTop = elements.consoleOutput.scrollHeight;
}

function clearConsole() {
    elements.consoleOutput.innerHTML = '';
}

function toggleConsole() {
    const panel = document.getElementById('console-panel');
    panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
