# AI-Generated
# Keep analysis dates at local midnight when converting them to timestamps.
analysis_day_starts <- function(days, tz = analysis_timezone) {
  as.POSIXct(as.character(days), tz = tz)
}

# AI-Generated
# Select one detection model so repeated detections are not counted together.
select_analysis_model <- function(analyses, det_model_id = NULL) {
  if (is.null(analyses) || nrow(analyses) == 0) return(analyses)
  if (is.null(det_model_id)) det_model_id <- Sys.getenv("DASHBOARD_DET_MODEL_ID", unset = "")
  model_ids <- unique(analyses$det_model_id)
  if (identical(det_model_id, "")) {
    if (length(model_ids) != 1) {
      stop("Set DASHBOARD_DET_MODEL_ID to select one of the available detection models.", call. = FALSE)
    }
    det_model_id <- model_ids
  }
  if (length(det_model_id) != 1 || is.na(det_model_id) || !det_model_id %in% model_ids) {
    stop("The selected detection model has no daily analysis results.", call. = FALSE)
  }
  analyses[analyses$det_model_id == det_model_id, , drop = FALSE]
}

# AI-Generated
# Convert stored counts into activity using assessed roles and the analysis timezone.
analysis_activity_rows <- function(analyses, det_model_id = NULL, tz = analysis_timezone) {
  analyses <- select_analysis_model(analyses, det_model_id)
  data.frame(
    camera_id = analyses$camera_id,
    det_model_id = analyses$det_model_id,
    date = as.Date(analyses$start_time, tz = tz),
    rat_count = ifelse(analyses$role == "prey", analyses$taxonomy_count, 0),
    predator_count = ifelse(analyses$role == "predator", analyses$taxonomy_count, 0),
    other_count = ifelse(analyses$role %in% c("prey", "predator"), 0, analyses$taxonomy_count),
    ai_activity = analyses$taxonomy_count * analyses$avg_confidence
  )
}

# AI-Generated
# Summarise one model's stored counts for the selected dashboard days.
daily_activity_logs <- function(dashboard_days, analyses = NULL, session = db_session, det_model_id = NULL, tz = analysis_timezone) {
  if (is.null(analyses)) analyses <- analysis_rows_with_species(session)
  if (is.null(analyses) || nrow(analyses) == 0) return(NULL)

  activities <- analysis_activity_rows(analyses, det_model_id, tz)
  activity_columns <- c("rat_count", "predator_count", "other_count", "ai_activity")
  daily_counts <- activities[activities$date %in% dashboard_days, c("date", activity_columns), drop = FALSE]
  if (nrow(daily_counts) > 0) {
    daily_counts <- stats::aggregate(daily_counts[activity_columns], daily_counts["date"], sum)
  }
  logs <- merge(data.frame(date = dashboard_days), daily_counts, by = "date", all.x = TRUE, sort = TRUE)
  for (column in activity_columns) {
    logs[[column]][is.na(logs[[column]])] <- 0
  }
  logs$det_model_id <- rep(unique(activities$det_model_id), nrow(logs))
  logs$timestamp <- analysis_day_starts(logs$date, tz)
  logs$predator_pressure <- calculate_predator_pressure(logs$rat_count, logs$predator_count)
  logs$predator_pressure_pct <- logs$predator_pressure * 100
  logs$trap_catch <- 0
  logs
}

# AI-Generated
# Fill each real camera's selected days from one model's stored counts.
camera_activity_logs <- function(dashboard_days, analyses = NULL, cameras = NULL, session = db_session, det_model_id = NULL, tz = analysis_timezone) {
  if (is.null(analyses)) analyses <- analysis_rows_with_species(session)
  if (is.null(cameras)) cameras <- fetch_cameras(session)
  if (is.null(analyses) || nrow(analyses) == 0 || nrow(cameras) == 0) return(data.frame())

  activities <- analysis_activity_rows(analyses, det_model_id, tz)
  count_columns <- c("rat_count", "predator_count", "other_count")
  camera_counts <- activities[activities$date %in% dashboard_days, c("camera_id", "date", count_columns), drop = FALSE]
  if (nrow(camera_counts) > 0) {
    camera_counts <- stats::aggregate(camera_counts[count_columns], camera_counts[c("camera_id", "date")], sum)
  }
  camera_days <- merge(cameras, data.frame(date = dashboard_days), by = NULL)
  logs <- merge(camera_days, camera_counts, by = c("camera_id", "date"), all.x = TRUE, sort = TRUE)
  for (column in count_columns) {
    logs[[column]][is.na(logs[[column]])] <- 0
  }
  logs$det_model_id <- rep(unique(activities$det_model_id), nrow(logs))
  logs$predator_pressure <- calculate_predator_pressure(logs$rat_count, logs$predator_count)
  logs
}
