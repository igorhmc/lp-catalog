from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base_class import Base

class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    disc_number: Mapped[int | None] = mapped_column(Integer)
    side: Mapped[str | None] = mapped_column(String(8))
    position: Mapped[str] = mapped_column(String(8))  # Para suportar formatos como "A1", "B2", etc
    title: Mapped[str] = mapped_column(String(255))
    duration: Mapped[str] = mapped_column(String(16))  # Formato "MM:SS"
    
    album_id: Mapped[int] = mapped_column(ForeignKey("albums.id", ondelete="CASCADE"), index=True)
    album = relationship("Album", back_populates="tracks")
