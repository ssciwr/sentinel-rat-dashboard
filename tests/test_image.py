import pytest
from sqlalchemy.exc import IntegrityError

from dashboard.db import image_crud
from dashboard.db.data_model import ImageCapture


def test_add_image_capture_creates_row(
    get_session, created_image, image_data, location_text, point_str
):
    created_image = created_image()

    assert created_image.id is not None
    assert created_image.camera_id == image_data["create"]["camera_id"]
    assert created_image.image_path == image_data["create"]["image_path"]
    assert location_text(
        get_session, ImageCapture, created_image.id
    ) == point_str.format(
        image_data["create"]["location"][0], image_data["create"]["location"][1]
    )


def test_add_image_capture_rejects_duplicate_image_path(
    get_session, created_image, image_data
):
    created_image()

    with pytest.raises(IntegrityError):
        image_crud.add(get_session, **image_data["create"])


def test_add_image_capture_defaults_to_not_analyzed_and_in_watch_folder(
    get_session, created_image
):
    created_image = created_image()

    assert created_image.analyzed_at is None
    assert created_image.file_status == "in_watch_folder"
    assert created_image.stored_path is None


def test_mark_image_as_analyzed(get_session, created_image):
    created_image = created_image()

    assert image_crud.mark_image_as_analyzed(get_session, created_image.id) is True

    updated_image = image_crud.get(get_session, created_image.id)
    assert updated_image is not None
    assert updated_image.analyzed_at is not None
    assert updated_image.file_status == "in_watch_folder"


def test_mark_image_as_analyzed_returns_false_for_unknown_image(get_session):
    assert image_crud.mark_image_as_analyzed(get_session, 9999) is False


def test_get_images_to_move_returns_only_analyzed_images_in_watch_folder(
    get_session, created_multi_images
):
    multi_images = created_multi_images()
    created_image1 = multi_images[0]
    created_image2 = multi_images[1]

    assert image_crud.get_images_to_move(get_session) == []

    image_crud.mark_image_as_analyzed(get_session, created_image1.id)
    image_crud.mark_image_as_analyzed(get_session, created_image2.id)
    image_crud.mark_image_as_moved(get_session, created_image2.id)

    images_to_move = image_crud.get_images_to_move(get_session)
    assert len(images_to_move) == 1
    assert images_to_move[0].id == created_image1.id


def test_mark_image_as_moved(get_session, created_image):
    created_image = created_image()
    image_crud.mark_image_as_analyzed(get_session, created_image.id)

    assert image_crud.mark_image_as_moved(get_session, created_image.id) is True

    updated_image = image_crud.get(get_session, created_image.id)
    assert updated_image is not None
    assert updated_image.file_status == "moved"
    assert updated_image.stored_path is None


def test_mark_image_as_moved_sets_stored_path(get_session, created_image, image_data):
    created_image = created_image()
    image_crud.mark_image_as_analyzed(get_session, created_image.id)

    assert (
        image_crud.mark_image_as_moved(
            get_session, created_image.id, stored_path="/archive/image.jpg"
        )
        is True
    )

    updated_image = image_crud.get(get_session, created_image.id)
    assert updated_image is not None
    assert updated_image.file_status == "moved"
    assert updated_image.stored_path == "/archive/image.jpg"
    assert updated_image.image_path == image_data["create"]["image_path"]


def test_mark_image_as_moved_rejects_duplicate_stored_path(
    get_session, created_multi_images
):
    multi_images = created_multi_images()
    created_image1 = multi_images[0]
    created_image2 = multi_images[1]
    image_crud.mark_image_as_analyzed(get_session, created_image1.id)
    image_crud.mark_image_as_analyzed(get_session, created_image2.id)
    image_crud.mark_image_as_moved(
        get_session, created_image1.id, stored_path="/archive/image.jpg"
    )

    with pytest.raises(IntegrityError):
        image_crud.mark_image_as_moved(
            get_session, created_image2.id, stored_path="/archive/image.jpg"
        )
    get_session.rollback()


def test_mark_image_as_moved_rejects_image_not_analyzed(get_session, created_image):
    created_image = created_image()

    with pytest.raises(ValueError):
        image_crud.mark_image_as_moved(get_session, created_image.id)

    unchanged_image = image_crud.get(get_session, created_image.id)
    assert unchanged_image is not None
    assert unchanged_image.file_status == "in_watch_folder"


def test_mark_image_as_moved_returns_false_for_unknown_image(get_session):
    assert image_crud.mark_image_as_moved(get_session, 9999) is False


def test_db_rejects_moved_image_not_analyzed(get_session, created_image):
    created_image = created_image()

    created_image.file_status = "moved"
    with pytest.raises(IntegrityError):
        get_session.commit()
    get_session.rollback()


def test_db_rejects_stored_path_for_image_not_moved(get_session, created_image):
    created_image = created_image()

    created_image.stored_path = "/archive/image.jpg"
    with pytest.raises(IntegrityError):
        get_session.commit()
    get_session.rollback()


def test_mark_image_as_missing_keeps_analyzed_at(get_session, created_multi_images):
    multi_images = created_multi_images()
    created_image1 = multi_images[0]
    created_image2 = multi_images[1]
    image_crud.mark_image_as_analyzed(get_session, created_image1.id)

    assert image_crud.mark_image_as_missing(get_session, created_image1.id) is True
    assert image_crud.mark_image_as_missing(get_session, created_image2.id) is True

    analyzed_missing = image_crud.get(get_session, created_image1.id)
    assert analyzed_missing is not None
    assert analyzed_missing.file_status == "missing"
    assert analyzed_missing.analyzed_at is not None

    not_analyzed_missing = image_crud.get(get_session, created_image2.id)
    assert not_analyzed_missing is not None
    assert not_analyzed_missing.file_status == "missing"
    assert not_analyzed_missing.analyzed_at is None


def test_mark_image_as_missing_returns_false_for_unknown_image(get_session):
    assert image_crud.mark_image_as_missing(get_session, 9999) is False


def test_file_status_cannot_change_once_out_of_watch_folder(get_session, created_image):
    created_image = created_image()
    image_crud.mark_image_as_analyzed(get_session, created_image.id)
    image_crud.mark_image_as_moved(get_session, created_image.id)

    with pytest.raises(ValueError):
        image_crud.mark_image_as_missing(get_session, created_image.id)
    with pytest.raises(ValueError):
        image_crud.mark_image_as_moved(get_session, created_image.id)


def test_mark_image_as_restored_keeps_analyzed_at(get_session, created_image):
    created_image = created_image()
    image_crud.mark_image_as_analyzed(get_session, created_image.id)
    image_crud.mark_image_as_missing(get_session, created_image.id)

    assert image_crud.mark_image_as_restored(get_session, created_image.id) is True

    restored_image = image_crud.get(get_session, created_image.id)
    assert restored_image is not None
    assert restored_image.file_status == "in_watch_folder"
    assert restored_image.analyzed_at is not None


def test_mark_image_as_restored_rejects_image_not_missing(get_session, created_image):
    created_image = created_image()

    with pytest.raises(ValueError):
        image_crud.mark_image_as_restored(get_session, created_image.id)

    image_crud.mark_image_as_analyzed(get_session, created_image.id)
    image_crud.mark_image_as_moved(get_session, created_image.id)
    with pytest.raises(ValueError):
        image_crud.mark_image_as_restored(get_session, created_image.id)


def test_mark_image_as_restored_returns_false_for_unknown_image(get_session):
    assert image_crud.mark_image_as_restored(get_session, 9999) is False


def test_get_images_by_file_status(get_session, created_multi_images):
    multi_images = created_multi_images()
    created_image1 = multi_images[0]
    created_image2 = multi_images[1]

    assert image_crud.get_images_by_file_status(get_session, "moved") == []

    image_crud.mark_image_as_analyzed(get_session, created_image1.id)
    image_crud.mark_image_as_moved(get_session, created_image1.id)
    image_crud.mark_image_as_missing(get_session, created_image2.id)

    moved_images = image_crud.get_images_by_file_status(get_session, "moved")
    assert [image.id for image in moved_images] == [created_image1.id]

    missing_images = image_crud.get_images_by_file_status(get_session, "missing")
    assert [image.id for image in missing_images] == [created_image2.id]

    assert image_crud.get_images_by_file_status(get_session, "in_watch_folder") == []


def test_get_images_in_period_returns_images_within_time_range(
    get_session, created_multi_images
):
    multi_images = created_multi_images()
    created_image1 = multi_images[0]
    created_image2 = multi_images[1]

    start_time = created_image2.captured_at  # 2024
    end_time = (
        created_image1.captured_at
    )  # image1 got timestamp from server default, which is after 2024

    images_in_period = image_crud.get_images_in_period(
        get_session, start_time, end_time
    )

    assert len(images_in_period) == 2
    assert images_in_period[0].id == created_image1.id
    assert images_in_period[1].id == created_image2.id

    images_in_period = image_crud.get_images_in_period(
        get_session, start_time=end_time, end_time=None
    )
    assert len(images_in_period) == 1
    assert images_in_period[0].id == created_image1.id


def test_refuse_direct_update(get_session, created_image, image_data):
    created_image = created_image()

    with pytest.raises(NotImplementedError):
        image_crud.update(
            get_session, created_image.id, {"image_path": "/new/path/to/image.jpg"}
        )
