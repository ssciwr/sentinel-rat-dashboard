from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text, Float, func

from sqlalchemy.dialects.postgresql import JSONB

from geoalchemy2 import Geometry

from .database import Base


class Camera(Base):
    """Camera table"""

    __tablename__ = "camera"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    location = Column(
        Geometry(geometry_type="POINT", srid=4326), nullable=False, index=True
    )
    description = Column(Text, nullable=True)
    installation_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), nullable=False, default="active")


class User(Base):
    """User table"""

    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Model(Base):
    """Model table"""

    __tablename__ = "model"

    id = Column(String(255), primary_key=True, autoincrement=True)  # Model ID
    name = Column(String(255), nullable=False)  # Model name
    version = Column(String(50), nullable=False)  # Model version
    description = Column(Text, nullable=True)  # Model description


class Detection(Base):
    """Detection table"""

    __tablename__ = "detection"

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    species = Column(JSONB, nullable=False)
    confidence = Column(Float, nullable=False)
    bounding_box = Column(JSONB, nullable=False)  # Store bounding box as JSON
    image_url = Column(Text, nullable=True)  # URL to the image
    place = Column(String(255), nullable=True)  # Place where the image was captured
    model_id = Column(
        String(255), ForeignKey("model.id"), nullable=True
    )  # Model ID used for detection
    user_id = Column(
        String(255), ForeignKey("user.id"), nullable=True
    )  # User who correct the detection, if any
