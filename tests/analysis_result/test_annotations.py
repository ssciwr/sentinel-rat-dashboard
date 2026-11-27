"""Check editor saves against PostgreSQL and the existing daily analysis."""

from datetime import timedelta
from functools import partial
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from dashboard.db.annotation_data import load_annotation_data
from dashboard.db.annotations import save_annotation
from dashboard.db.analysis_result import DeletedImagesError, daily_analysis_result_crud
from dashboard.db.data_model import ClassificationCorrection, DetectionCorrection

from .helpers import BBOX, DAY, add_detection, add_image, at, compute, daily_results

CORNERS = {"x0": 12, "y0": 18, "x1": 42, "y1": 58}


def correction_count(session, correction_model):
    """AI-Generated.
    Count saved corrections when checking for duplicates or incomplete saves.
    """
    return session.scalar(select(func.count()).select_from(correction_model))


@pytest.fixture
def editor(get_session, setup):
    """AI-Generated.
    Provide the existing rat-to-mouse example with a classified camera image.
    """
    image = add_image(get_session, setup, at(9))
    detection = add_detection(get_session, setup, image, [(setup.rat, 0.9)])
    payload = dict(
        app_user_id=setup.user1.id,
        image_capture_id=image.id,
        detection_id=str(detection.id),
        bbox=CORNERS,
        species="Mus musculus",
    )
    return SimpleNamespace(
        session=get_session,
        setup=setup,
        image=image,
        detection=detection,
        save=partial(save_annotation, get_session, **payload),
        count=partial(correction_count, get_session),
    )


@pytest.mark.parametrize("event_type", ["bbox_edited", "species_changed"])
def test_repeated_edits_update_the_existing_correction(editor, event_type):
    """AI-Generated. Keep one reviewer correction while preserving the model result."""
    saved = editor.save(event_type=event_type)
    editor.save(event_type=event_type)
    correction = editor.session.scalar(select(DetectionCorrection))
    assert saved["target_id"] == str(editor.detection.id)
    assert editor.count(DetectionCorrection) == 1
    assert correction.corrected_bbox == {"x": 12, "y": 18, "width": 30, "height": 40}
    assert editor.detection.bbox == BBOX


def test_species_change_rebuilds_daily_counts_and_survives_reopening(editor):
    """AI-Generated. Move a rat count to mouse and read it in a fresh session."""
    compute(editor.session)
    editor.save(event_type="species_changed")
    last_frame = add_image(editor.session, editor.setup, at(23, 59))
    add_image(editor.session, editor.setup, at(0, day=DAY + timedelta(days=1)))
    add_image(editor.session, editor.setup, at(9), camera=editor.setup.camera2)
    with Session(editor.session.bind) as reopened:
        records = load_annotation_data(
            reopened, editor.image.camera_id, DAY.isoformat()
        )
    assert [frame["image_id"] for frame in records["images"]] == [
        str(editor.image.id),
        str(last_frame.id),
    ]
    assert records["detections"][0]["label"] == "Mus musculus"
    assert (
        editor.detection.species_classifications[0].taxonomy_id == editor.setup.rat.id
    )
    assert list(daily_results(editor.session).values()) == [(1, 1.0)]


def test_added_detection_can_be_edited_and_removed_without_duplicates(editor):
    """AI-Generated. Reuse the saved ID when editing a box created in the browser."""
    created = editor.save(event_type="bbox_created")
    editor.save(event_type="bbox_edited", detection_id=created["target_id"])
    editor.save(event_type="bbox_deleted", detection_id=created["target_id"])
    correction = editor.session.scalar(select(DetectionCorrection))
    assert editor.count(DetectionCorrection) == 1
    assert correction.action == "remove"
    assert (
        correction.classification_corrections[0].corrected_taxonomy_id
        == editor.setup.mouse.id
    )
    assert len(editor.image.object_detections) == 1


def test_removing_a_model_detection_clears_its_daily_count(editor):
    """AI-Generated. Remove a counted detection while retaining the original row."""
    compute(editor.session)
    editor.save(event_type="bbox_deleted")
    assert daily_results(editor.session) == {}
    assert editor.session.scalar(select(DetectionCorrection)).action == "remove"
    assert editor.detection.bbox == BBOX


def test_unknown_species_rolls_back_an_added_box(editor):
    """AI-Generated. Reject a slightly changed species without saving half a correction."""
    with pytest.raises(ValueError, match="species"):
        editor.save(event_type="bbox_created", species="Mus musculus?")
    assert editor.count(DetectionCorrection) == 0
    assert editor.count(ClassificationCorrection) == 0
    assert editor.detection.bbox == BBOX


@pytest.mark.parametrize("invalid_x", [-1, float("inf"), float("nan"), 43])
def test_invalid_box_does_not_change_saved_data(editor, invalid_x):
    """AI-Generated. Reject reversed, negative, and nonfinite coordinates."""
    with pytest.raises(ValueError):
        editor.save(event_type="bbox_edited", bbox=CORNERS | {"x0": invalid_x})
    assert editor.count(DetectionCorrection) == 0
    assert editor.count(ClassificationCorrection) == 0
    assert editor.detection.bbox == BBOX


def test_detection_from_another_image_is_rejected(editor):
    """AI-Generated. Keep image references intact when an event names the wrong image."""
    other_image = add_image(editor.session, editor.setup, at(10))
    with pytest.raises(ValueError, match="belong"):
        editor.save(event_type="bbox_edited", image_capture_id=other_image.id)
    assert editor.count(DetectionCorrection) == 0
    assert editor.detection.image_capture_id == editor.image.id
    assert editor.detection.bbox == BBOX


def test_recompute_failure_rolls_back_species_and_box_together(editor):
    """AI-Generated. Preserve both tables if daily analysis cannot be updated."""
    recompute = daily_analysis_result_crud
    with patch.object(recompute, "recompute_for_image", side_effect=ValueError):
        with pytest.raises(ValueError):
            editor.save(event_type="species_changed")
    assert editor.count(DetectionCorrection) == 0
    assert editor.count(ClassificationCorrection) == 0
    assert editor.detection.bbox == BBOX


def test_deleted_images_warning_still_saves_the_correction(editor):
    """AI-Generated. Return a warning flag without exposing an internal error."""
    recompute = daily_analysis_result_crud
    error = DeletedImagesError(DAY, editor.setup.camera1.id, 2, 1)
    with patch.object(recompute, "recompute_for_image", side_effect=error):
        saved = editor.save(event_type="species_changed")
    assert saved["analysis_warning"] is True
    assert editor.session.scalar(select(DetectionCorrection)).corrected_bbox["x"] == 12
    assert (
        editor.session.scalar(select(ClassificationCorrection)).corrected_taxonomy_id
        == editor.setup.mouse.id
    )
