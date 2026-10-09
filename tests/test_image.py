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


def test_mark_image_for_deletion(get_session, created_image):
    created_image = created_image()

    image_crud.mark_image_for_deletion(get_session, created_image.id)

    updated_image = image_crud.get(get_session, created_image.id)
    assert updated_image is not None
    assert updated_image.tobe_deleted is True


def test_get_images_to_delete_returns_only_images_marked_for_deletion(
    get_session, created_multi_images
):
    multi_images = created_multi_images()
    created_image1 = multi_images[0]

    images_to_delete = image_crud.get_images_to_delete(get_session)
    assert len(images_to_delete) == 0

    image_crud.mark_image_for_deletion(get_session, created_image1.id)

    images_to_delete = image_crud.get_images_to_delete(get_session)
    assert len(images_to_delete) == 1
    assert images_to_delete[0].id == created_image1.id
    assert images_to_delete[0].tobe_deleted is True


def test_add_image_capture_defaults_is_moved_to_false(get_session, created_image):
    created_image = created_image()

    assert created_image.is_moved is False


def test_add_image_capture_with_is_moved(get_session, created_camera, image_data):
    created_camera()
    created_image = image_crud.add(
        get_session,
        **{**image_data["create"], "tobe_deleted": True, "is_moved": True},
    )

    assert created_image.is_moved is True


def test_add_image_capture_rejects_moved_image_not_marked_for_deletion(
    get_session, created_camera, image_data
):
    created_camera()

    with pytest.raises(ValueError):
        image_crud.add(get_session, **{**image_data["create"], "is_moved": True})


def test_db_rejects_moved_image_not_marked_for_deletion(get_session, created_image):
    created_image = created_image()

    created_image.is_moved = True
    with pytest.raises(IntegrityError):
        get_session.commit()
    get_session.rollback()


def test_mark_image_as_moved(get_session, created_image):
    created_image = created_image()
    image_crud.mark_image_for_deletion(get_session, created_image.id)

    assert image_crud.mark_image_as_moved(get_session, created_image.id) is True

    updated_image = image_crud.get(get_session, created_image.id)
    assert updated_image is not None
    assert updated_image.is_moved is True


def test_mark_image_as_moved_rejects_image_not_marked_for_deletion(
    get_session, created_image
):
    created_image = created_image()

    with pytest.raises(ValueError):
        image_crud.mark_image_as_moved(get_session, created_image.id)

    unchanged_image = image_crud.get(get_session, created_image.id)
    assert unchanged_image is not None
    assert unchanged_image.is_moved is False


def test_mark_image_as_moved_returns_false_for_missing_image(get_session):
    assert image_crud.mark_image_as_moved(get_session, 9999) is False


def test_get_moved_images_returns_only_moved_images(
    get_session, created_multi_images
):
    multi_images = created_multi_images()
    created_image1 = multi_images[0]
    created_image2 = multi_images[1]

    moved_images = image_crud.get_moved_images(get_session)
    assert len(moved_images) == 0

    # marked for deletion but not moved yet, so still excluded
    image_crud.mark_image_for_deletion(get_session, created_image1.id)
    image_crud.mark_image_for_deletion(get_session, created_image2.id)
    image_crud.mark_image_as_moved(get_session, created_image1.id)

    moved_images = image_crud.get_moved_images(get_session)
    assert len(moved_images) == 1
    assert moved_images[0].id == created_image1.id
    assert moved_images[0].is_moved is True


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
