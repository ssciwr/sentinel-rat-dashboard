# Fetch annotations
fetch_annotation_data <- function(camera_id, day) {
  session <- create_db_session()
  on.exit(session$close())
  records <- reticulate::import("dashboard.db.annotation_data")$load_annotation_data(
    session,
    as.integer(camera_id),
    format(day, "%Y-%m-%d")
  )
  images <- dplyr::bind_rows(records$images)
  if (nrow(images) == 0) {
    images <- data.frame(
      image_id = character(), camera_name = character(), timestamp = numeric(),
      image_path = character(), detection_count = integer()
    )
  }
  images$timestamp <- as.POSIXct(images$timestamp, origin = "1970-01-01", tz = "UTC")
  detections <- dplyr::bind_rows(records$detections)
  if (nrow(detections) == 0) {
    detections <- data.frame(image_id = character(), detection_id = character(), genus_detected = character())
  }
  list(images = images, detections = detections)
}

# Complete species list, which the user can choose from to create a "class" correction
fetch_annotation_species <- function(session = db_session) {
  sort(vapply(taxonomy_crud$select(session), function(taxonomy) {
    species_label(taxonomy$genus, taxonomy$species)
  }, character(1)))
}

# Pass to Python ORM for the saving action
save_detection_annotation <- function(payload, app_user_id) {
  session <- create_db_session()
  on.exit(session$close())
  reticulate::import("dashboard.db.annotations")$save_annotation(
    session,
    app_user_id = as.integer(app_user_id),
    image_capture_id = as.integer(payload$image_id),
    detection_id = payload$detection_id,
    event_type = payload$event_type,
    bbox = payload$bbox,
    species = payload$species
  )
}

# Used on load and whenever the window is reopened
fetch_saved_image_annotations <- function(image_id) {
  session <- create_db_session()
  on.exit(session$close())
  records <- reticulate::import("dashboard.db.annotation_data")$load_image_detections(session, as.integer(image_id))
  if (length(records) == 0) return(list())
  image_annotations(image_id, dplyr::bind_rows(records))
}
