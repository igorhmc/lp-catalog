from pydantic import BaseModel, ConfigDict

class ArtistBase(BaseModel):
    name: str
    country: str | None = None

class ArtistCreate(ArtistBase):
    pass

class ArtistOut(ArtistBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
