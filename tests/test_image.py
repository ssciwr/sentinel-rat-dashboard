from dashboard.db import image_crud
from dashboard.db.data_model import ImageCapture
import pytest


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
