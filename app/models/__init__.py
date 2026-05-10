from .artist import Artist
from .album import Album
from .track import Track
from .copy import Copy, CopyPhoto, CopyLocationHistory
from .storage import StorageUnit, StorageSlot

# Para facilitar imports
__all__ = [
    "Artist",
    "Album",
    "Track",
    "Copy",
    "CopyPhoto",
    "CopyLocationHistory",
    "StorageUnit",
    "StorageSlot",
]
