from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from api.deps import get_session
from models.artist import Artist
from schemas.artist import ArtistCreate, ArtistOut

router = APIRouter()

@router.get("/", response_model=list[ArtistOut])
async def list_artists(db: AsyncSession = Depends(get_session)):
    res = await db.execute(select(Artist).order_by(Artist.name))
    return res.scalars().all()

@router.get("/count")
async def count_artists(db: AsyncSession = Depends(get_session)):
    res = await db.execute(select(func.count(Artist.id)))
    return {"count": res.scalar_one() or 0}

@router.post("/", response_model=ArtistOut, status_code=201)
async def create_artist(payload: ArtistCreate, db: AsyncSession = Depends(get_session)):
    exists = await db.execute(select(Artist).where(Artist.name == payload.name))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Artist already exists")
    obj = Artist(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj