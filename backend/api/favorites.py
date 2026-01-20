"""
DouyinStream Pro v2 - Favorites API
Endpoints for managing favorite streams.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException

from .models import Favorite, FavoriteCreate, FavoriteUpdate, FavoritesList

logger = logging.getLogger(__name__)
router = APIRouter()

# Data file
DATA_DIR = Path(__file__).parent.parent / "data"
FAVORITES_FILE = DATA_DIR / "favorites.json"


def _load_favorites() -> List[Favorite]:
    """Load favorites from file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if not FAVORITES_FILE.exists():
        return []
    
    try:
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [Favorite(**item) for item in data]
    except Exception as e:
        logger.error(f"Error loading favorites: {e}")
        return []


def _save_favorites(favorites: List[Favorite]) -> None:
    """Save favorites to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            data = [fav.model_dump(mode='json') for fav in favorites]
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error saving favorites: {e}")
        raise HTTPException(status_code=500, detail="Failed to save favorites")


@router.get("", response_model=FavoritesList)
async def list_favorites():
    """Get all favorite streams with their live status."""
    favorites = _load_favorites()
    
    # Get live status from LiveChecker if available
    live_urls = []  #TODO: integrate with LiveChecker
    
    return FavoritesList(
        favorites=favorites,
        live_urls=live_urls
    )


@router.post("", response_model=Favorite)
async def add_favorite(request: FavoriteCreate):
    """Add a new favorite stream."""
    favorites = _load_favorites()
    
    # Check if already exists
    for fav in favorites:
        if fav.url == request.url:
            raise HTTPException(status_code=409, detail="URL already in favorites")
    
    new_fav = Favorite(
        url=request.url,
        alias=request.alias,
        added_at=datetime.now()
    )
    
    favorites.append(new_fav)
    _save_favorites(favorites)
    
    logger.info(f"⭐ Added favorite: {request.url}")
    return new_fav


@router.get("/{url:path}", response_model=Favorite)
async def get_favorite(url: str):
    """Get a specific favorite by URL."""
    favorites = _load_favorites()
    
    for fav in favorites:
        if fav.url == url:
            return fav
    
    raise HTTPException(status_code=404, detail="Favorite not found")


@router.patch("/{url:path}", response_model=Favorite)
async def update_favorite(url: str, request: FavoriteUpdate):
    """Update a favorite's properties (alias, etc)."""
    favorites = _load_favorites()
    
    for i, fav in enumerate(favorites):
        if fav.url == url:
            if request.alias is not None:
                favorites[i].alias = request.alias
            
            _save_favorites(favorites)
            return favorites[i]
    
    raise HTTPException(status_code=404, detail="Favorite not found")


@router.delete("/{url:path}")
async def delete_favorite(url: str):
    """Remove a favorite stream."""
    favorites = _load_favorites()
    
    for i, fav in enumerate(favorites):
        if fav.url == url:
            del favorites[i]
            _save_favorites(favorites)
            logger.info(f"🗑️ Removed favorite: {url}")
            return {"success": True, "message": "Favorite removed"}
    
    raise HTTPException(status_code=404, detail="Favorite not found")


@router.post("/{url:path}/played")
async def mark_played(url: str):
    """Update play count and last played time."""
    favorites = _load_favorites()
    
    for i, fav in enumerate(favorites):
        if fav.url == url:
            favorites[i].play_count += 1
            favorites[i].last_played = datetime.now()
            _save_favorites(favorites)
            return {"success": True, "play_count": favorites[i].play_count}
    
    # Not a favorite, that's okay
    return {"success": True, "play_count": 0}


@router.get("/live/all")
async def get_live_favorites():
    """Get all favorites that are currently live."""
    # TODO: Integrate with LiveChecker
    favorites = _load_favorites()
    
    return {
        "favorites": favorites,
        "live_count": 0,
        "message": "Live checking integration pending"
    }
