import logging
from pathlib import Path
from typing import Optional

import aiofiles
import httpx

from core.config import get_settings
from schemas.album import AlbumSearch
from schemas.album import Track

BASE_URL = "https://api.discogs.com"
logger = logging.getLogger(__name__)

class DiscogsService:
    def __init__(self):
        self.settings = get_settings()
        self.headers = {}
        if self.settings.DISCOGS_TOKEN:
            self.headers["Authorization"] = f"Discogs token={self.settings.DISCOGS_TOKEN}"
        else:
            logger.warning("Discogs token is not configured")
        
        self.covers_dir = Path(self.settings.COVERS_DIR)
        self.covers_dir.mkdir(exist_ok=True)

    async def search_releases(self, query: str, limit: int = 100, page: int = 1) -> dict:
        """Busca álbuns no Discogs com o termo fornecido"""
        async with httpx.AsyncClient(base_url=BASE_URL, headers=self.headers, timeout=30) as client:
            params = {
                "q": query,
                "type": "release",
                "format": "Vinyl",
                "per_page": min(limit, 100),
                "page": page,
            }
            response = await client.get("/database/search", params=params)
            response.raise_for_status()
            data = response.json()

            albums = []
            for item in data.get("results", []):
                item_id = item.get("id")
                if not item_id:
                    continue

                try:
                    title = item.get("title", "")
                    if not title:
                        continue

                    artist_name = "Desconhecido"
                    if item.get("artist"):
                        artist_name = item["artist"]
                    elif " - " in title:
                        artist_name, title = [part.strip() for part in title.split(" - ", 1)]

                    year = item.get("year")
                    genre = item.get("genre", [None])[0] if item.get("genre") else None
                    cover_url = item.get("cover_image") or item.get("thumb")

                    release = await self.get_release(item_id)
                    if not release.get("artists"):
                        continue

                    artist_name = release["artists"][0]["name"].strip()
                    title = release.get("title", title)
                    if not year:
                        year = release.get("year")
                    if not genre:
                        genre = release.get("genres", [None])[0]
                    if not cover_url and "images" in release:
                        cover_url = next(
                            (
                                img["uri"]
                                for img in release["images"]
                                if img.get("type") == "primary" and "uri" in img
                            ),
                            next((img["uri"] for img in release["images"] if "uri" in img), None),
                        )

                    tracks = []
                    for track_data in release.get("tracklist", []):
                        if not track_data.get("position") or not track_data.get("title"):
                            continue
                        tracks.append(
                            Track(
                                position=track_data["position"],
                                title=track_data["title"],
                                duration=track_data.get("duration", "00:00"),
                            )
                        )

                    albums.append(
                        AlbumSearch(
                            title=title,
                            artist=artist_name,
                            year=year,
                            genre=genre,
                            discogs_id=item_id,
                            cover_url=cover_url,
                            tracks=tracks,
                        )
                    )
                except Exception:
                    logger.exception("Failed to process Discogs release %s", item_id)
                    continue

            return {
                "albums": albums,
                "pagination": {
                    "page": data.get("pagination", {}).get("page", page),
                    "pages": data.get("pagination", {}).get("pages", 1),
                    "total": data.get("pagination", {}).get("items", len(albums)),
                },
            }

    async def get_release(self, release_id: int) -> dict:
        """Obtém informações detalhadas de um release específico"""
        async with httpx.AsyncClient(base_url=BASE_URL, headers=self.headers, timeout=20) as client:
            response = await client.get(f"/releases/{release_id}")
            response.raise_for_status()
            return response.json()

    async def download_cover(self, album_info: AlbumSearch) -> Optional[str]:
        """Baixa a capa do álbum e retorna o caminho relativo onde foi salva"""
        if not album_info.cover_url:
            return None

        # Cria nome do arquivo baseado no ID do Discogs para evitar conflitos
        filename = f"{album_info.discogs_id}.jpg"
        file_path = self.covers_dir / filename
        rel_path = str(Path('covers') / filename)

        if file_path.exists():
            return rel_path

        async with httpx.AsyncClient() as client:
            response = await client.get(album_info.cover_url)
            if response.status_code != 200:
                return None

            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(response.content)

        return rel_path
