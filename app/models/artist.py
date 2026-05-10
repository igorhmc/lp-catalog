from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base_class import Base

class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)

    albums = relationship("Album", back_populates="artist", cascade="all, delete-orphan")
