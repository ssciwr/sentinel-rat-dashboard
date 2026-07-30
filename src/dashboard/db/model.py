from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Index

from sqlalchemy.dialects.postgresql import JSONB

from geoalchemy2 import Geometry

from .database import Base


class Camera(Base):
    """Camera table"""

    __tablename__ = "camera"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    location = Column(
        Geometry(geometry_type="POINT", srid=4326), nullable=False, index=True
    )
    description = Column(Text, nullable=True)
    installation_date = Column(DateTime, default=datetime.now())
    status = Column(String(50), nullable=False, default="active")


class User(Base):
    """User table"""

    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive
    created_at = Column(DateTime, default=datetime.now())
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())


class Detection(Base):
    """Detection table"""

    __tablename__ = "detection"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    camera_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.now(), index=True)
    object_type = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    bounding_box = Column(JSONB, nullable=False)  # Store bounding box as JSON
    image_url = Column(String(255), nullable=True)  # URL to the image
