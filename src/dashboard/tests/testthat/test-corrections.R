library(dplyr)

# AI generated helper for the tests below:
correction_server <- function(input, output, session) {
  for (source_file in c("server/annotation_server.R", "R/image_functions.R", "R/label_functions.R", "ui/components/icons.R", "ui/settings.R")) {
    source(file.path("../..", source_file), local = TRUE)
  }
  camera_images <- data.frame(
    image_id = "1", camera_name = "Test camera", date = as.Date("2026-09-01"),
    timestamp = as.POSIXct("2026-09-01 08:30:00", tz = "UTC"), detection_count = 1L,
    image_path = normalizePath("../../www/camera-placeholder.png")
  )
  detections <- data.frame(
    image_id = "1", detection_id = "1", x = 10, y = 20, width = 80, height = 60,
    label = "Rattus rattus", confidence = 0.9, origin_type = "model", origin_name = "Test model"
  )
  predator_heat_low_hex <- "#245c78"
  predator_heat_high_hex <- "#1f5f3a"

  map_snapshot <- function(value, camera_logs = NULL) {
    data.frame(camera_id = 1L, camera_name = "Test camera", rodent_activity = 1L, predator_count = 0L)
  }
  selected_map_day <- function(value) as.Date("2026-09-01")
  species_correction <- list(
    event_type = "species_changed", image_id = "1", detection_id = "1",
    species = "Mus musculus", annotations = list(list(id = "1", properties = list(Species = "Mus musculus")))
  )
  editor_store <- new.env(parent = emptyenv())
  editor_store$detections <- list()
  editor_store$messages <- list()

  session$sendCustomMessage <- function(type, message) editor_store$messages[[type]] <- message
  fetch_saved_image_annotations <- function(image_id) image_annotations(image_id, detections)
  fetch_annotation_data <- function(camera_id, day) {
    stopifnot(camera_id == 1L, day == as.Date("2026-09-01"))
    list(images = camera_images, detections = detections)
  }
  save_correction <- function(payload, app_user_id) {
    if (isTRUE(editor_store$fail)) stop("private-database-detail")
    detection_id <- payload$detection_id
    if (payload$event_type == "bbox_created") detection_id <- "added-42"
    if (!detection_id %in% c("1", "added-42")) stop("unknown detection")
    editor_store$detections[[detection_id]] <- list(species = payload$species, reviewer = app_user_id)
    list(target_id = detection_id, analysis_warning = FALSE)
  }
  store <- make_auth_store()
  auth <- register_auth_server(input, session, store$fetch)
  state <- list(
    selected_camera_name = reactiveVal("Test camera"), selected_image_index = reactiveVal(1),
    camera_day_logs = reactiveVal(data.frame()),
    last_correction = reactiveVal(NULL), annotation_modal_open = reactiveVal(FALSE),
    annotation_overrides = reactiveVal(list())
  )
  register_annotation_server(input, output, session, state, auth, save_correction)
}


test_that("Edit button for correction is always present, shows create account option if logged out", {
  for (signed_in in c(FALSE, TRUE)) testServer(correction_server, {
    if (signed_in) login_settings(session)
    inspector <- output$inspector_panel$html
    expect_match(inspector, 'id="open_annotation"')
    expect_match(output$camera_image_panel$html, "open_annotation")
    expect_false(grepl("Create account to correct", inspector, fixed = TRUE))
    expect_identical(auth$can_manage_cameras(), signed_in)
  })
})

test_that("Corrections data corresponds to the open inspector window (only)", {
  testServer(correction_server, {
    session$setInputs(detection_annotation_changed = species_correction)
    expect_false(state$annotation_modal_open())
    expect_null(state$last_correction())
    expect_identical(state$annotation_overrides(), list())
  })
})

# AI-Generated minor tests about basic UI functionality
test_that("closing the camera view clears its contents", {
  testServer(correction_server, {
    session$setInputs(close_inspector = 1)
    expect_null(state$selected_camera_name())
    expect_null(output$inspector_panel)
    expect_false(state$annotation_modal_open())
  })
})

test_that("signing out or losing access prevents corrections in an open editor", {
  for (logout in c(TRUE, FALSE)) testServer(correction_server, {
    login_settings(session)
    session$setInputs(open_annotation = 1)
    saved_annotations <- state$annotation_overrides()[["1"]]
    if (logout) session$setInputs(settings_logout = 1) else store$rows$is_active[1] <- FALSE
    session$setInputs(detection_annotation_changed = species_correction)
    expect_identical(editor_store$detections, list())
    expect_identical(state$annotation_overrides()[["1"]], saved_annotations)
    expect_identical(editor_store$messages$restore_annotations$annotations, saved_annotations)
  })
})

test_that("signed-in reviewers save corrections under their account", {
  testServer(correction_server, {
    login_settings(session)
    session$setInputs(open_annotation = 1, detection_annotation_changed = species_correction)
    expect_match(state$last_correction(), "^Saved.*Mus musculus")
    expect_identical(editor_store$detections[["1"]]$reviewer, 1L)
    expect_identical(state$annotation_overrides()[["1"]], species_correction$annotations)
  })
})

test_that("failed saves restore the saved boxes without exposing database errors", {
  testServer(correction_server, {
    login_settings(session)
    session$setInputs(open_annotation = 1)
    editor_store$fail <- TRUE
    session$setInputs(detection_annotation_changed = species_correction)
    expect_match(state$last_correction(), "^Not saved")
    expect_identical(editor_store$detections, list())
    expect_match(editor_store$messages$restore_annotations$annotations[[1]]$properties$Species, "Rattus rattus")
    expect_false(grepl("private-database-detail", output$correction_status$html, fixed = TRUE))
  })
})

test_that("signed-out visitors cannot submit box or species changes", {
  for (event_type in c("bbox_created", "bbox_edited", "bbox_deleted", "species_changed")) testServer(correction_server, {
    session$setInputs(open_annotation = 1)
    saved_annotations <- state$annotation_overrides()[["1"]]
    session$setInputs(detection_annotation_changed = modifyList(species_correction, list(event_type = event_type)))
    expect_match(state$last_correction(), "^Not saved")
    expect_identical(editor_store$detections, list())
    expect_identical(state$annotation_overrides()[["1"]], saved_annotations)
  })
})

test_that("created boxes keep their saved identity on subsequent edits", {
  testServer(correction_server, {
    login_settings(session)
    session$setInputs(open_annotation = 1)
    session$setInputs(detection_annotation_changed = modifyList(species_correction, list(event_type = "bbox_created", detection_id = "browser-uuid")))
    session$setInputs(detection_annotation_changed = modifyList(species_correction, list(event_type = "bbox_edited", detection_id = "browser-uuid")))
    expect_identical(names(editor_store$detections), "added-42")
    expect_identical(editor_store$detections[["added-42"]]$species, "Mus musculus")
    expect_match(state$last_correction(), "^Saved.*bbox_edited")
  })
})
