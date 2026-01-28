"""
DouyinStream Pro v2 - WebSocket Event Manager
Manages WebSocket connections for real-time log streaming.
"""

import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._log_buffer: List[Dict[str, Any]] = []
        self._buffer_size = 100  # Keep last 100 messages
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"🔌 WebSocket connected. Total: {len(self.active_connections)}")
        
        # Send buffered logs to new client
        if self._log_buffer:
            await websocket.send_json({
                "type": "history",
                "data": self._log_buffer
            })
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"🔌 WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Send message to all connected clients."""
        # Add to buffer
        self._log_buffer.append(message)
        if len(self._log_buffer) > self._buffer_size:
            self._log_buffer.pop(0)
        
        # Broadcast to all
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)
    
    async def log(self, message: str, level: str = "INFO", source: str = "system"):
        """Send a log message to all clients."""
        await self.broadcast({
            "type": "log",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "source": source,
                "message": message
            }
        })
    
    async def stream_event(self, event: str, data: Dict[str, Any]):
        """Send a stream-related event."""
        await self.broadcast({
            "type": "stream_event",
            "event": event,
            "data": data
        })
    
    async def status_update(self, url: str, status: str, extra: Dict[str, Any] = None):
        """Send a stream status update."""
        payload = {
            "type": "status",
            "data": {
                "url": url,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }
        }
        if extra:
            payload["data"].update(extra)
        await self.broadcast(payload)
