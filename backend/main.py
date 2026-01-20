"""
DouyinStream Pro v2 - FastAPI Backend
Main entry point with all routes and WebSocket support.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api import streams, favorites, system
from core.cookie_manager import CookieManager
from core.live_checker import LiveChecker
from ws.events import ConnectionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
cookie_manager: Optional[CookieManager] = None
live_checker: Optional[LiveChecker] = None
ws_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    global cookie_manager, live_checker
    
    # Startup
    logger.info("🚀 Starting DouyinStream Pro v2 Backend...")
    
    # Initialize cookie manager
    cookie_manager = CookieManager()
    await cookie_manager.load_cookies()
    
    # Initialize live checker (but don't start yet)
    live_checker = LiveChecker(cookie_manager, ws_manager)
    
    logger.info("✅ Backend ready!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    if live_checker:
        await live_checker.stop()
    logger.info("👋 Goodbye!")


# Create FastAPI app
app = FastAPI(
    title="DouyinStream Pro v2",
    description="Modern streaming viewer for Douyin/TikTok",
    version="2.0.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection helpers
def get_cookie_manager() -> CookieManager:
    return cookie_manager


def get_live_checker() -> LiveChecker:
    return live_checker


def get_ws_manager() -> ConnectionManager:
    return ws_manager


# Include API routers
app.include_router(
    streams.router,
    prefix="/api/streams",
    tags=["streams"]
)
app.include_router(
    favorites.router,
    prefix="/api/favorites",
    tags=["favorites"]
)
app.include_router(
    system.router,
    prefix="/api/system",
    tags=["system"]
)


# WebSocket endpoint for real-time logs
@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, handle incoming messages
            data = await websocket.receive_text()
            # Could handle commands here
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "cookies_loaded": cookie_manager.has_valid_cookies() if cookie_manager else False
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
