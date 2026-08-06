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

from sqlalchemy.orm import relationship, Mapped, mapped_column

from sqlalchemy.dialects.postgresql import JSONB

from geoalchemy2 import Geometry

from .database import Base


class Camera(Base):
    """Camera table"""

    __tablename__ = "camera"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)
    installation_date: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(
        Enum("active", "inactive", "maintenance", name="camera_status"),
        nullable=False,
        default="active",
    )

    # relationship to CameraLocationHistory
    location_history = relationship(
        "CameraLocationHistory", back_populates="camera", cascade="all, delete-orphan"
    )

    # relationship to ImageCapture
    images = relationship(
        "ImageCapture", back_populates="camera", cascade="all, delete-orphan"
    )

    # relationship to DailyAnalysisResult
    daily_analysis_results = relationship(
        "DailyAnalysisResult", back_populates="camera", cascade="all, delete-orphan"
    )


class CameraLocationHistory(Base):
    """CameraLocationHistory table"""

    __tablename__ = "camera_location_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("camera.id"), nullable=False, index=True
    )
    location: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=False, index=True
    )
    valid_from: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Null means still valid

    # relationship to Camera
    camera = relationship(
        "Camera", back_populates="location_history", foreign_keys=[camera_id]
    )


class ImageCapture(Base):
    """Image table"""

    __tablename__ = "image_capture"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("camera.id"), nullable=False, index=True
    )
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    uploaded_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    location: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=False, index=True
    )  # Fetched from the camera's location at the time of capture, since camera might be moved
    tobe_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # Flag for deletion when storage is full

    # relationship to Camera
    camera = relationship("Camera", back_populates="images", foreign_keys=[camera_id])

    # relationship to ObjectDetection
    object_detections = relationship(
        "ObjectDetection", back_populates="image_capture", cascade="all, delete-orphan"
    )

    # relationship to DetectionCorrection
    detection_corrections = relationship(
        "DetectionCorrection",
        back_populates="image_capture",
        cascade="all, delete-orphan",
    )


class MLModel(Base):
    """MLModel table"""

    __tablename__ = "ml_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=True)
    task: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g., 'detection', 'classification'
    description: Mapped[str] = mapped_column(
        Text, nullable=True
    )  # additional information about the model

    # relationships to ObjectDetection and SpeciesClassification
    object_detections = relationship(
        "ObjectDetection", back_populates="ml_model", cascade="all, delete-orphan"
    )
    species_classifications = relationship(
        "SpeciesClassification", back_populates="ml_model", cascade="all, delete-orphan"
    )

    # relationship to DetectionCorrection
    detection_corrections = relationship(
        "DetectionCorrection", back_populates="ml_model", cascade="all, delete-orphan"
    )


class ObjectDetection(Base):
    """ObjectDetection table"""

    __tablename__ = "object_detection"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image_capture_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("image_capture.id"), nullable=False, index=True
    )
    det_model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ml_model.id"), nullable=False, index=True
    )  # detection model used for this detection
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )  # Timestamp when the detection was created
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bbox: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )  # Store bounding box as JSON
    detected_class: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # e.g. 'animal'

    # relationship to ImageCapture
    image_capture = relationship(
        "ImageCapture",
        back_populates="object_detections",
        foreign_keys=[image_capture_id],
    )

    # relationship to MLModel
    ml_model = relationship(
        "MLModel", back_populates="object_detections", foreign_keys=[det_model_id]
    )

    # relationship to SpeciesClassification
    species_classifications = relationship(
        "SpeciesClassification",
        back_populates="object_detection",
        cascade="all, delete-orphan",
    )

    # relationship to DetectionCorrection
    detection_corrections = relationship(
        "DetectionCorrection",
        back_populates="object_detection",
        cascade="all, delete-orphan",
    )


class Taxonomy(Base):
    """Taxonomy table"""

    __tablename__ = "taxonomy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kingdom: Mapped[str] = mapped_column(String(255), nullable=True)
    phylum: Mapped[str] = mapped_column(String(255), nullable=True)
    class_name: Mapped[str] = mapped_column(String(255), nullable=True)
    order: Mapped[str] = mapped_column(String(255), nullable=True)
    family: Mapped[str] = mapped_column(String(255), nullable=True)
    genus: Mapped[str] = mapped_column(String(255), nullable=True)
    species: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    common_name: Mapped[str] = mapped_column(String(255), nullable=True)

    # species, genus, and family should be unique in combination
    __table_args__ = (
        UniqueConstraint("species", "genus", name="uq_taxonomy_species_genus"),
    )

    # relationship to SpeciesClassification
    species_classifications = relationship(
        "SpeciesClassification", back_populates="taxonomy", cascade="all, delete-orphan"
    )

    # relationship to ClassificationCorrection
    classification_corrections = relationship(
        "ClassificationCorrection",
        back_populates="taxonomy",
        cascade="all, delete-orphan",
    )

    # relationship to DailyAnalysisResult
    daily_analysis_results = relationship(
        "DailyAnalysisResult", back_populates="taxonomy", cascade="all, delete-orphan"
    )


class SpeciesClassification(Base):
    """SpeciesClassification table"""

    __tablename__ = "species_classification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_detection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("object_detection.id"), nullable=False, index=True
    )
    taxonomy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy.id"), nullable=False, index=True
    )
    clas_model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ml_model.id"), nullable=False, index=True
    )  # classification model used for this classification
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )  # Timestamp when the classification was created
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # relationship to ObjectDetection
    object_detection = relationship(
        "ObjectDetection",
        back_populates="species_classifications",
        foreign_keys=[object_detection_id],
    )

    # relationship to Taxonomy
    taxonomy = relationship(
        "Taxonomy", back_populates="species_classifications", foreign_keys=[taxonomy_id]
    )

    # relationship to MLModel
    ml_model = relationship(
        "MLModel",
        back_populates="species_classifications",
        foreign_keys=[clas_model_id],
    )

    # relationship to ClassificationCorrection
    classification_corrections = relationship(
        "ClassificationCorrection",
        back_populates="species_classification",
        cascade="all, delete-orphan",
    )


class AppUser(Base):
    """User table"""

    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationship to DetectionCorrection
    detection_corrections = relationship(
        "DetectionCorrection", back_populates="user", cascade="all, delete-orphan"
    )

    # relationship to ClassificationCorrection
    classification_corrections = relationship(
        "ClassificationCorrection", back_populates="user", cascade="all, delete-orphan"
    )


class DetectionCorrection(Base):
    """Detection Correction table"""

    __tablename__ = "detection_correction"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_detection_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("object_detection.id"), nullable=True, index=True
    )
    # in case a new detection is added,
    # object_detection_id will be null, and new_detection_id will be set
    new_detection_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        unique=True,
    )
    # repeat image_capture_id and det_model_id in case a new detection is added
    image_capture_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("image_capture.id"), nullable=False, index=True
    )
    det_model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ml_model.id"), nullable=False, index=True
    )
    app_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("app_user.id"), nullable=False, index=True
    )
    corrected_bbox: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )  # Store corrected bounding box as JSON
    corrected_class: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # e.g. 'animal'
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    last_updated: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )  # Timestamp when the correction was made
    action: Mapped[str] = mapped_column(
        Enum("add", "remove", "update", name="detection_correction_action"),
        nullable=False,
    )  # Action taken: add, remove, or update the detection

    # relationship to ObjectDetection
    object_detection = relationship(
        "ObjectDetection",
        back_populates="detection_corrections",
        foreign_keys=[object_detection_id],
    )

    # relationship to AppUser
    user = relationship(
        "AppUser", back_populates="detection_corrections", foreign_keys=[app_user_id]
    )

    # relationship to ImageCapture
    image_capture = relationship(
        "ImageCapture",
        back_populates="detection_corrections",
        foreign_keys=[image_capture_id],
    )

    # relationship to MLModel
    ml_model = relationship(
        "MLModel", back_populates="detection_corrections", foreign_keys=[det_model_id]
    )

    # relationship to ClassificationCorrection for new_detection_id
    classification_corrections = relationship(
        "ClassificationCorrection",
        back_populates="detection_correction",
        primaryjoin=(
            "DetectionCorrection.new_detection_id == "
            "foreign(ClassificationCorrection.new_obj_det_id)"
        ),
        cascade="all, delete-orphan",
    )

    # unique constraint
    __table_args__ = (
        # store only the lastest correction of user for a given object_detection_id
        UniqueConstraint(
            "object_detection_id",
            "app_user_id",
            name="uq_detection_correction_obj_detection_user",
        ),
        # same for user and new_detection_id
        UniqueConstraint(
            "new_detection_id",
            "app_user_id",
            name="uq_detection_correction_new_detection_user",
        ),
    )


class ClassificationCorrection(Base):
    """Classification Correction table"""

    __tablename__ = "classification_correction"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    species_classification_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("species_classification.id"), nullable=True, index=True
    )
    # if a new detection is added, a new classification will be created
    new_obj_det_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("detection_correction.new_detection_id"),
        nullable=True,
        index=True,
    )
    new_classification_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )
    app_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("app_user.id"), nullable=False, index=True
    )
    corrected_taxonomy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy.id"), nullable=False, index=True
    )
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    last_updated: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )  # Timestamp when the correction was made
    action: Mapped[str] = mapped_column(
        Enum("add", "update", name="classification_correction_action"),
        nullable=False,
    )  # Action taken: add or update the classification

    # relationship to SpeciesClassification
    species_classification = relationship(
        "SpeciesClassification",
        back_populates="classification_corrections",
        foreign_keys=[species_classification_id],
    )

    # relationship to Taxonomy
    taxonomy = relationship(
        "Taxonomy",
        back_populates="classification_corrections",
        foreign_keys=[corrected_taxonomy_id],
    )

    # relationship to AppUser
    user = relationship(
        "AppUser",
        back_populates="classification_corrections",
        foreign_keys=[app_user_id],
    )

    # relationship to DetectionCorrection for new_obj_det_id
    detection_correction = relationship(
        "DetectionCorrection",
        back_populates="classification_corrections",
        primaryjoin=(
            "DetectionCorrection.new_detection_id == "
            "foreign(ClassificationCorrection.new_obj_det_id)"
        ),
    )

    # unique constraint
    __table_args__ = (
        # store only the lastest correction of user for a given species_classification_id
        UniqueConstraint(
            "species_classification_id",
            "app_user_id",
            name="uq_classification_correction_species_classification_user",
        ),
        # same for user and new_classification_id
        UniqueConstraint(
            "new_classification_id",
            "app_user_id",
            name="uq_classification_correction_new_classification_user",
        ),
    )


class DailyAnalysisResult(Base):
    """DailyAnalysisResult table"""

    __tablename__ = "daily_analysis_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("camera.id"), nullable=False, index=True
    )
    start_time: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_time: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    taxonomy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy.id"), nullable=False, index=True
    )
    taxonomy_count: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Total number of detected taxonomy instances in this period
    avg_confidence: Mapped[float] = mapped_column(
        Float, nullable=False
    )  # Average confidence of detections in this period

    __table_args__ = (
        UniqueConstraint(
            "camera_id", "start_time", "taxonomy_id", name="uq_daily_analysis"
        ),
    )

    # relationship to Camera
    camera = relationship(
        "Camera", back_populates="daily_analysis_results", foreign_keys=[camera_id]
    )

    # relationship to Taxonomy
    taxonomy = relationship(
        "Taxonomy", back_populates="daily_analysis_results", foreign_keys=[taxonomy_id]
    )
