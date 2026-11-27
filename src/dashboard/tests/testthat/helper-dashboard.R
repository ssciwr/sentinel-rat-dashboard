# AI generated temporary helper

dashboard_test_dir <- normalizePath("../..")
dashboard_test_analyses <- data.frame(
  camera_id = rep(rep(1:3, each = 2), 2), det_model_id = 10L,
  start_time = as.POSIXct(rep(c("2026-09-30 18:30:00", "2026-10-01 18:30:00"), each = 6), tz = "UTC"),
  species_label = rep(c("Rattus rattus", "Pavo cristatus"), 6),
  role = rep(c("prey", "predator"), 6),
  taxonomy_count = c(3L, 1L, 0L, 0L, 2L, 3L, 4L, 1L, 0L, 0L, 1L, 3L), avg_confidence = 0.9
)
dashboard_test_cameras <- data.frame(
  camera_id = 1:3, camera_name = c("CAM01", "CAM02", "CAM03"),
  lat = c(7.001, 7.002, 7.003), lon = c(81.001, 81.002, 81.003)
)
dashboard_test_annotations <- list(
  images = data.frame(
    image_id = "1", camera_name = "CAM01", date = as.Date("2026-10-01"),
    timestamp = as.POSIXct("2026-10-01 08:30:00", tz = "UTC"),
    image_path = file.path(dashboard_test_dir, "www", "camera-placeholder.png"), detection_count = 1L
  ),
  detections = data.frame(
    detection_id = "1", image_id = "1", label = "Rattus rattus", genus_detected = "Rattus",
    confidence = 0.9, origin_type = "machine", origin_name = "Test model",
    x = 10, y = 20, width = 80, height = 60
  ),
  species = c("Rattus rattus", "Pavo cristatus")
)

# AI-Generated
# Load application data with fixed database results for dashboard tests.
dashboard_test_data <- function(analyses = dashboard_test_analyses, species = dashboard_test_annotations$species) {
  dashboard <- new.env(parent = environment())
  dashboard$analysis_timezone <- "Asia/Colombo"
  # AI-Generated
  # Return the daily results supplied by the test.
  dashboard$analysis_rows_with_species <- function() analyses
  # AI-Generated
  # Return three camera locations without opening a database session.
  dashboard$fetch_cameras <- function() dashboard_test_cameras
  # AI-Generated
  # Return the species options supplied by the test.
  dashboard$fetch_annotation_species <- function() species
  # AI-Generated
  # Load application helpers while keeping database access inside the test fixtures.
  dashboard$source <- function(file, local = TRUE) {
    if (!file %in% c("R/db.R", "R/annotation_db.R")) sys.source(file, envir = dashboard)
  }
  withr::with_dir(dashboard_test_dir, sys.source("R/data.R", envir = dashboard))
  dashboard$source <- NULL
  dashboard
}
