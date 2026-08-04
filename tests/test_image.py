from dashboard.db import image, camera
from dashboard.db.data_model import ImageCapture
import pytest


def _add_image_capture(session, camera_data, image_data):
    # add camera first to satisfy foreign key constraint
    camera.add_camera(session, **camera_data)

    return image.add_image_capture(session, **image_data)


def test_add_image_capture_creates_row(
    get_session, image_data, location_text, point_str, camera_data
):
    created_image = _add_image_capture(
        get_session, camera_data["create"], image_data["create"]
    )

    assert created_image.id is not None
    assert created_image.camera_id == image_data["create"]["camera_id"]
    assert created_image.image_path == image_data["create"]["image_path"]
    assert location_text(
        get_session, ImageCapture, created_image.id
    ) == point_str.format(
        image_data["create"]["location"][0], image_data["create"]["location"][1]
    )


def test_select_and_get_image_capture_return_saved_rows(
    get_session, image_data, camera_data
):
    created_image = _add_image_capture(
        get_session, camera_data["create"], image_data["create"]
    )

    images = image.select_image_captures(get_session)

    assert len(images) == 1
    assert images[0].id == created_image.id
    assert images[0].camera_id == image_data["create"]["camera_id"]

    fetched_image = image.get_image_capture(get_session, created_image.id)
    assert fetched_image is not None
    assert fetched_image.id == created_image.id
    assert fetched_image.image_path == image_data["create"]["image_path"]


def test_get_images_by_filter_returns_filtered_rows(
    get_session, image_data, camera_data
):
    created_image1 = _add_image_capture(
        get_session, camera_data["create"], image_data["create"]
    )
    created_image2 = _add_image_capture(
        get_session, camera_data["create"], image_data["create_with_timestamps"]
    )

    filtered_images = image.get_images_by_filter(
        get_session, camera_id=image_data["create"]["camera_id"]
    )

    assert len(filtered_images) == 2
    assert filtered_images[0].id == created_image1.id
    assert filtered_images[0].camera_id == image_data["create"]["camera_id"]
    assert filtered_images[1].id == created_image2.id
    assert filtered_images[1].camera_id == image_data["create"]["camera_id"]


def test_get_images_by_filter_raises_value_error_when_no_filters(get_session):
    with pytest.raises(ValueError):
        image.get_images_by_filter(get_session)


def test_get_images_by_filter_returns_empty_list_when_no_matches(
    get_session, image_data, camera_data
):
    _add_image_capture(get_session, camera_data["create"], image_data["create"])

    filtered_images = image.get_images_by_filter(
        get_session, camera_id=image_data["create"]["camera_id"] + 1
    )

    assert len(filtered_images) == 0


def test_get_images_by_filter_returns_empty_list_when_no_rows(get_session):
    filtered_images = image.get_images_by_filter(get_session, camera_id=1)

    assert len(filtered_images) == 0


def test_mark_image_for_deletion(get_session, image_data, camera_data):
    created_image = _add_image_capture(
        get_session, camera_data["create"], image_data["create"]
    )

    image.mark_image_for_deletion(get_session, created_image.id)

    updated_image = image.get_image_capture(get_session, created_image.id)
    assert updated_image is not None
    assert updated_image.tobe_deleted is True


def test_get_images_to_delete_returns_only_images_marked_for_deletion(
    get_session, image_data, camera_data
):
    created_image1 = _add_image_capture(
        get_session, camera_data["create"], image_data["create"]
    )
    created_image2 = _add_image_capture(
        get_session, camera_data["create"], image_data["create_with_timestamps"]
    )

    images_to_delete = image.get_images_to_delete(get_session)
    assert len(images_to_delete) == 0

    image.mark_image_for_deletion(get_session, created_image1.id)

    images_to_delete = image.get_images_to_delete(get_session)
    assert len(images_to_delete) == 1
    assert images_to_delete[0].id == created_image1.id
    assert images_to_delete[0].tobe_deleted is True


def test_get_images_in_period_returns_images_within_time_range(
    get_session, image_data, camera_data
):
    created_image1 = _add_image_capture(
        get_session, camera_data["create"], image_data["create"]
    )
    created_image2 = _add_image_capture(
        get_session, camera_data["create"], image_data["create_with_timestamps"]
    )

    start_time = created_image2.captured_at  # 2024
    end_time = (
        created_image1.captured_at
    )  # image1 got timestamp from server default, which is after 2024

    images_in_period = image.get_images_in_period(get_session, start_time, end_time)

    assert len(images_in_period) == 2
    assert images_in_period[0].id == created_image1.id
    assert images_in_period[1].id == created_image2.id

    images_in_period = image.get_images_in_period(
        get_session, start_time=end_time, end_time=None
    )
    assert len(images_in_period) == 1
    assert images_in_period[0].id == created_image1.id


def test_delete_image_capture(get_session, image_data, camera_data):
    created_image = _add_image_capture(
        get_session, camera_data["create"], image_data["create"]
    )

    assert image.delete_image_capture(get_session, created_image.id) is True

    deleted_image = image.get_image_capture(get_session, created_image.id)
    assert deleted_image is None
