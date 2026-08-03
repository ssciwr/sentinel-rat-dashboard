from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    DateTime,
    Text,
    Float,
    func,
    Boolean,
    Enum,
    UniqueConstraint,
)

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
    status = Column(
        Enum("active", "inactive", "maintenance", name="camera_status"),
        nullable=False,
        default="active",
    )


class CameraLocationHistory(Base):
    """CameraLocationHistory table"""

    __tablename__ = "camera_location_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey("camera.id"), nullable=False, index=True)
    location = Column(
        Geometry(geometry_type="POINT", srid=4326), nullable=False, index=True
    )
    valid_from = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to = Column(DateTime(timezone=True), nullable=True)  # Null means still valid


class ImageCapture(Base):
    """Image table"""

    __tablename__ = "image_capture"

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey("camera.id"), nullable=False, index=True)
    image_path = Column(Text, nullable=False)
    captured_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    uploaded_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    location = Column(
        Geometry(geometry_type="POINT", srid=4326), nullable=False, index=True
    )  # Fetched from the camera's location at the time of capture, since camera might be moved


class Model(Base):
    """Model table"""

    __tablename__ = "model"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    task = Column(String(50), nullable=False)  # e.g., 'detection', 'classification'
    description = Column(Text, nullable=True)  # additional information about the model


class ObjectDetection(Base):
    """ObjectDetection table"""

    __tablename__ = "object_detection"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_capture_id = Column(
        Integer, ForeignKey("image_capture.id"), nullable=False, index=True
    )
    det_model_id = Column(
        Integer, ForeignKey("model.id"), nullable=False, index=True
    )  # detection model used for this detection
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )  # Timestamp when the detection was created
    confidence = Column(Float, nullable=False)
    bbox = Column(JSONB, nullable=False)  # Store bounding box as JSON
    detected_class = Column(String(255), nullable=False)  # e.g. 'animal'


class Taxonomy(Base):
    """Taxonomy table"""

    __tablename__ = "taxonomy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kingdom = Column(String(255), nullable=True)
    phylum = Column(String(255), nullable=True)
    class_name = Column(String(255), nullable=True)
    order = Column(String(255), nullable=True)
    family = Column(String(255), nullable=True)
    genus = Column(String(255), nullable=True)
    species = Column(String(255), nullable=False, index=True)
    common_name = Column(String(255), nullable=True)

    # species, genus, and family should be unique in combination
    __table_args__ = (
        UniqueConstraint("species", "genus", name="uq_taxonomy_species_genus"),
    )


class SpeciesClassification(Base):
    """SpeciesClassification table"""

    __tablename__ = "species_classification"

    id = Column(Integer, primary_key=True, autoincrement=True)
    object_detection_id = Column(
        Integer, ForeignKey("object_detection.id"), nullable=False, index=True
    )
    taxonomy_id = Column(Integer, ForeignKey("taxonomy.id"), nullable=False, index=True)
    clas_model_id = Column(
        Integer, ForeignKey("model.id"), nullable=False, index=True
    )  # classification model used for this classification
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )  # Timestamp when the classification was created
    confidence = Column(Float, nullable=False)


class AppUser(Base):
    """User table"""

    __tablename__ = "app_user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DetectionCorrection(Base):
    """Detection Correction table"""

    __tablename__ = "detection_correction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    object_detection_id = Column(
        Integer, ForeignKey("object_detection.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("app_user.id"), nullable=False, index=True)
    corrected_bbox = Column(
        JSONB, nullable=False
    )  # Store corrected bounding box as JSON
    corrected_class = Column(String(255), nullable=False)  # e.g. 'animal'
    comment = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )  # Timestamp when the correction was made
    action = Column(
        Enum("add", "remove", "modify", name="correction_det_action"),
        nullable=False,
        default="modify",
    )


class ClassificationCorrection(Base):
    """Classification Correction table"""

    __tablename__ = "classification_correction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    species_classification_id = Column(
        Integer, ForeignKey("species_classification.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("app_user.id"), nullable=False, index=True)
    corrected_taxonomy_id = Column(
        Integer, ForeignKey("taxonomy.id"), nullable=False, index=True
    )
    comment = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )  # Timestamp when the correction was made


class DailyAnalysisResult(Base):
    """DailyAnalysisResult table"""

    __tablename__ = "daily_analysis_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey("camera.id"), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    taxonomy_id = Column(Integer, ForeignKey("taxonomy.id"), nullable=True, index=True)
    taxonomy_count = Column(
        Integer, nullable=False
    )  # Total number of detected taxonomy instances in this period
    avg_confidence = Column(
        Float, nullable=False
    )  # Average confidence of detections in this period

    __table_args__ = (
        UniqueConstraint(
            "camera_id", "start_time", "taxonomy_id", name="uq_daily_analysis"
        ),
    )
