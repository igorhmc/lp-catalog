from db.base_class import Base

# importe dos modelos para registrar no Base
from models.artist import Artist  # noqa
from models.album import Album    # noqa
from models.track import Track    # noqa
from models.copy import Copy, CopyPhoto, CopyLocationHistory  # noqa
from models.storage import StorageUnit, StorageSlot  # noqa

# Garanta que todos os modelos estejam registrados no Base
__all__ = ["Base", "Artist", "Album", "Track", "Copy", "CopyPhoto", "CopyLocationHistory", "StorageUnit", "StorageSlot"]
