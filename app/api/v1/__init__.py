from .albums import router as albums_router
from .artists import router as artists_router
from .copies import router as copies_router
from .health import router as health_router

__all__ = ["albums_router", "artists_router", "copies_router", "health_router"]
