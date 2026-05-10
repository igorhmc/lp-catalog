from fastapi import APIRouter, Depends, HTTPException, Query
import httpx
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import get_session
from models.album import Album
from models.artist import Artist
from models.track import Track
from schemas.album import AlbumCreate, AlbumOut, AlbumSearch
from services.discogs import DiscogsService
from utils.storage import build_location_code

router = APIRouter()

# Listar todos os álbuns
@router.get("/", response_model=list[AlbumOut])
async def list_albums(db: AsyncSession = Depends(get_session)):
    """Lista todos os álbuns ordenados por ano e título
    Nota: Como o schema de saída inclui as faixas (tracks), precisamos fazer eager load
    das relações em ambiente assíncrono para evitar MissingGreenlet ao serializar.
    """
    res = await db.execute(
        select(Album)
        .order_by(Album.year.desc(), Album.title)
        .options(
            selectinload(Album.artist),
            selectinload(Album.tracks),
        )
    )
    return res.scalars().all()

# Contagem de álbuns (mais leve para dashboards)
@router.get("/count")
async def count_albums(db: AsyncSession = Depends(get_session)):
    res = await db.execute(select(func.count(Album.id)))
    return {"count": res.scalar_one() or 0}

# Busca no Discogs
@router.get("/search-raw")
async def search_discogs_raw(q: str, discogs: DiscogsService = Depends(lambda: DiscogsService())):
    """Endpoint de teste que retorna os dados brutos do Discogs"""
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "q": q,
                "type": "release",
                "format": "Vinyl",
            }
            headers = discogs.headers
            r = await client.get(
                "https://api.discogs.com/database/search",
                params=params,
                headers=headers,
            )
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Discogs request failed with status {exc.response.status_code}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Discogs request failed") from exc

# Busca no Discogs com processamento
@router.get("/search")
async def search_albums(
    q: str = Query(..., min_length=1, description="Termo de busca para álbum/artista"),
    page: int = Query(default=1, ge=1, description="Página de resultados"),
    discogs: DiscogsService = Depends(lambda: DiscogsService())
):
    """Busca álbuns no Discogs (lista simples com 50 itens por página e informações de paginação)."""
    try:
        if not q.strip():
            raise HTTPException(
                status_code=400,
                detail="O termo de busca não pode estar vazio"
            )

        response = await discogs.search_releases(q.strip(), limit=5, page=page)
        if not response or not response.get('albums'):
            return {'albums': [], 'pagination': {'page': page, 'pages': 1, 'total': 0}}

        # Garantir que os resultados correspondam ao schema
        validated_results = []
        for album in response['albums']:
            try:
                # Converter para o modelo AlbumSearch
                album_dict = {
                    "title": str(album.title),
                    "artist": str(album.artist),
                    "year": int(album.year) if album.year else None,
                    "genre": str(album.genre) if album.genre else None,
                    "discogs_id": int(album.discogs_id),
                    "cover_url": str(album.cover_url) if album.cover_url else None,
                    "notes": str(album.notes) if getattr(album, "notes", None) else None,
                    "tracks": [
                        {
                            "position": str(track.position),
                            "title": str(track.title),
                            "duration": str(track.duration)
                        }
                        for track in album.tracks
                    ] if album.tracks else []
                }
                validated_album = AlbumSearch.create_safe(**album_dict)
                validated_results.append(validated_album)
            except Exception:
                continue

        return {
            'albums': validated_results,
            'pagination': response.get('pagination', {'page': page, 'pages': 1, 'total': len(validated_results)})
        }

    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Discogs request failed with status {exc.response.status_code}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Discogs request failed") from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Erro ao realizar a busca no Discogs"
        ) from exc

# Criar álbum manualmente
@router.post("/manual", response_model=AlbumOut, status_code=201)
async def create_manual_album(
    album: AlbumCreate,
    db: AsyncSession = Depends(get_session)
):
    """Cria um novo álbum manualmente"""
    if not album.artist_id and not album.artist_name:
        raise HTTPException(
            status_code=400,
            detail="Either artist_id or artist_name must be provided"
        )

    # Se foi fornecido o nome do artista, busca ou cria
    if album.artist_name:
        artist_query = await db.execute(
            select(Artist).filter(Artist.name == album.artist_name)
        )
        artist = artist_query.scalar()
        if not artist:
            artist = Artist(name=album.artist_name)
            db.add(artist)
            await db.flush()  # Para gerar o ID do artista
        album.artist_id = artist.id
    resolved_artist_id = album.artist_id

    # Verifica se o álbum já existe
    exists = await db.execute(
        select(Album).filter(
            Album.title == album.title,
            Album.year == album.year,
            Album.artist_id == resolved_artist_id,
        )
    )
    if exists.first():
        raise HTTPException(
            status_code=400,
            detail="Album already exists"
        )

    # Cria o álbum
    album_payload = album.model_dump(exclude={'tracks', 'artist_name'})
    album_payload["location_code"] = build_location_code(
        album_payload.get("storage_unit"),
        album_payload.get("storage_niche"),
        album_payload.get("storage_position"),
    )
    new_album = Album(**album_payload)
    db.add(new_album)
    await db.flush()  # garante ID do álbum

    # Cria as faixas
    if album.tracks:
        for track_data in album.tracks:
            track = Track(
                album_id=new_album.id,
                position=track_data.position,
                title=track_data.title,
                duration=track_data.duration
            )
            db.add(track)

    await db.commit()
    
    # Recarrega o álbum com todos os relacionamentos
    await db.refresh(new_album, ['artist', 'tracks'])
    return new_album

# Criar álbum do Discogs
@router.post("/", response_model=AlbumOut, status_code=201)
async def create_album(
    album: AlbumSearch,
    db: AsyncSession = Depends(get_session),
    discogs: DiscogsService = Depends(lambda: DiscogsService())
):
    """Cria um novo álbum a partir dos dados do Discogs"""
    # Verifica se o álbum já existe
    exists = await db.execute(
        select(Album).filter(Album.discogs_id == album.discogs_id)
    )
    if exists.first():
        raise HTTPException(
            status_code=400,
            detail="Album already exists"
        )

    # Busca ou cria o artista
    artist_query = await db.execute(
        select(Artist).filter(Artist.name == album.artist)
    )
    artist = artist_query.scalar()
    if not artist:
        artist = Artist(name=album.artist)
        db.add(artist)
        await db.flush()  # Para gerar o ID do artista

    # Baixa a capa se disponível
    cover_path = None
    if album.cover_url:
        cover_path = await discogs.download_cover(album)

    # Cria o álbum
    new_album = Album(
        title=album.title,
        year=album.year,
        genre=album.genre,
        storage_unit=album.storage_unit,
        storage_niche=album.storage_niche,
        storage_position=album.storage_position,
        location_code=build_location_code(
            album.storage_unit,
            album.storage_niche,
            album.storage_position,
        ),
        artist_id=artist.id,
        discogs_id=album.discogs_id,
        cover_path=cover_path,
        notes=album.notes,
    )
    db.add(new_album)
    await db.flush()  # Para gerar o ID do álbum

    # Cria as faixas
    if hasattr(album, 'tracks'):
        for track_data in album.tracks:
            track = Track(
                album_id=new_album.id,
                position=track_data.position,
                title=track_data.title,
                duration=track_data.duration
            )
            db.add(track)

    await db.commit()
    
    # Recarrega o álbum com todos os relacionamentos
    await db.refresh(new_album, ['artist', 'tracks'])
    return new_album

# Obter álbum por ID
@router.get("/id/{album_id}", response_model=AlbumOut)
async def get_album(album_id: int, db: AsyncSession = Depends(get_session)):
    """Retorna os detalhes de um álbum específico"""
    res = await db.execute(
        select(Album)
        .filter(Album.id == album_id)
        .options(
            selectinload(Album.artist),
            selectinload(Album.tracks)
        )
    )
    album = res.scalar_one_or_none()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    return album

# Atualizar álbum
@router.put("/id/{album_id}", response_model=AlbumOut)
async def update_album(
    album_id: int,
    album_data: AlbumCreate,
    db: AsyncSession = Depends(get_session)
):
    """Atualiza um álbum existente"""
    # Busca o álbum existente
    res = await db.execute(
        select(Album)
        .filter(Album.id == album_id)
        .options(
            selectinload(Album.artist),
            selectinload(Album.tracks)
        )
    )
    album = res.scalar_one_or_none()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    # Busca ou cria o artista se necessário
    if album_data.artist_name:
        artist_query = await db.execute(
            select(Artist).filter(Artist.name == album_data.artist_name)
        )
        artist = artist_query.scalar()
        if not artist:
            artist = Artist(name=album_data.artist_name)
            db.add(artist)
            await db.flush()
        album_data.artist_id = artist.id

    # Atualiza os campos do álbum
    clearable_fields = {"year", "genre", "notes", "storage_unit", "storage_niche", "storage_position"}
    for field, value in album_data.model_dump(exclude={'tracks', 'artist_name'}).items():
        if value is not None or field in clearable_fields:
            setattr(album, field, value)

    album.location_code = build_location_code(
        album.storage_unit,
        album.storage_niche,
        album.storage_position,
    )

    # Remove todas as faixas existentes
    await db.execute(delete(Track).filter(Track.album_id == album_id))

    # Adiciona as novas faixas
    if album_data.tracks:
        for track_data in album_data.tracks:
            if track_data.position and track_data.title:  # Só adiciona faixas com dados válidos
                track = Track(
                    album_id=album_id,
                    position=track_data.position,
                    title=track_data.title,
                    duration=track_data.duration or "00:00"
                )
                db.add(track)

    await db.commit()
    
    # Recarrega o álbum com todos os relacionamentos
    await db.refresh(album, ['artist', 'tracks'])
    return album

# Remover álbum
@router.delete("/id/{album_id}", status_code=204)
async def delete_album(album_id: int, db: AsyncSession = Depends(get_session)):
    """Remove um álbum e suas faixas"""
    # Primeiro verifica se o álbum existe
    res = await db.execute(
        select(Album).filter(Album.id == album_id)
    )
    album = res.scalar_one_or_none()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # Remove o álbum (as faixas serão removidas em cascata)
    await db.execute(delete(Album).filter(Album.id == album_id))
    await db.commit()
    return None
