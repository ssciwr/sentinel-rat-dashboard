library(testthat)

source("../../R/metrics.R", local = TRUE)
source("../../R/analysis.R", local = TRUE)

# Load conversion functions without importing Python or opening a database session.
for (definition in parse("../../R/db.R")) {
  if (is.call(definition) && identical(definition[[1]], as.name("<-")) &&
      is.call(definition[[3]]) && identical(definition[[3]][[1]], as.name("function"))) {
    eval(definition)
  }
}

analysis_timezone <- "Asia/Colombo"
analysis_days <- as.Date(c("2026-10-01", "2026-10-02", "2026-10-03"))
analysis_examples <- data.frame(
  camera_id = c(1L, 1L, 1L, 1L, 2L, 1L),
  det_model_id = c(10L, 10L, 10L, 20L, 10L, 10L),
  role = c("prey", "predator", "not assessed", "prey", "prey", "prey"),
  start_time = as.POSIXct(c(rep("2026-09-30 18:30:00", 5), "2026-10-01 18:30:00"), tz = "UTC"),
  taxonomy_count = c(2L, 1L, 4L, 200L, 3L, 5L),
  avg_confidence = c(0.9, 0.8, 0.5, 0.9, 0.6, 0.4)
)
analysis_cameras <- data.frame(camera_id = 1:2, camera_name = c("CAM01", "CAM02"))

# AI-Generated
# Keep two models' observations separate when selecting daily results.
test_that("multiple detection models require an explicit selection", {
  selected <- select_analysis_model(analysis_examples, 10L)
  expect_error(select_analysis_model(analysis_examples, ""), "DASHBOARD_DET_MODEL_ID")
  expect_equal(unique(selected$det_model_id), 10L)
  expect_equal(nrow(selected), 5)
  expect_false(200L %in% selected$taxonomy_count)
})

# AI-Generated
# Select a configured model or use the only available one.
test_that("model selection respects configuration and single-model datasets", {
  withr::local_envvar(c(DASHBOARD_DET_MODEL_ID = "20"))
  configured <- select_analysis_model(analysis_examples)
  single_model <- select_analysis_model(analysis_examples[analysis_examples$det_model_id == 10L, ], "")
  expect_equal(unique(configured$det_model_id), 20L)
  expect_equal(configured$taxonomy_count, 200L)
  expect_equal(unique(single_model$det_model_id), 10L)
})

# AI-Generated
# Reject absent, missing, and combined model selections.
test_that("invalid model choices cannot combine or silently replace results", {
  expect_error(select_analysis_model(analysis_examples, 0L), "no daily analysis results")
  expect_error(select_analysis_model(analysis_examples, NA_integer_), "no daily analysis results")
  expect_error(select_analysis_model(analysis_examples, c(10L, 20L)), "no daily analysis results")
})

# AI-Generated
# Keep unassessed species separate from prey and predators.
test_that("database roles determine activity counts", {
  activities <- analysis_activity_rows(analysis_examples, 10L)
  expect_equal(activities$rat_count, c(2, 0, 0, 3, 5))
  expect_equal(activities$predator_count, c(0, 1, 0, 0, 0))
  expect_equal(activities$other_count, c(0, 0, 4, 0, 0))
})

# AI-Generated
# Count a single assessed role without requiring another role to be present.
test_that("prey-only, predator-only, and unassessed datasets remain usable", {
  for (role in c("prey", "predator", "not assessed")) {
    example <- analysis_examples[1, ]
    example$role <- role
    activities <- analysis_activity_rows(example, 10L)
    expect_equal(activities$rat_count, if (role == "prey") 2 else 0)
    expect_equal(activities$predator_count, if (role == "predator") 2 else 0)
    expect_equal(activities$other_count, if (role == "not assessed") 2 else 0)
  }
})

# AI-Generated
# Assign Sri Lankan midnight to its local analysis day.
test_that("stored timestamps follow the configured analysis timezone", {
  local_days <- analysis_activity_rows(analysis_examples, 10L)$date
  utc_days <- analysis_activity_rows(analysis_examples, 10L, tz = "UTC")$date
  expect_equal(local_days, analysis_days[c(1, 1, 1, 1, 2)])
  expect_equal(utc_days, as.Date(c(rep("2026-09-30", 4), "2026-10-01")))
  expect_equal(as.numeric(analysis_day_starts(analysis_days[1])), as.numeric(analysis_examples$start_time[1]))
})

# AI-Generated
# Sum cameras within one model and fill days without observations.
test_that("daily activity uses stored totals without counting another model", {
  logs <- daily_activity_logs(analysis_days, analysis_examples, det_model_id = 10L)
  expect_equal(logs$rat_count, c(5, 5, 0))
  expect_equal(logs$predator_count, c(1, 0, 0))
  expect_equal(logs$other_count, c(4, 0, 0))
  expect_equal(logs$ai_activity, c(6.4, 2, 0))
  expect_equal(logs$det_model_id, rep(10L, 3))
})

# AI-Generated
# Keep plot timestamps and annotation bounds at local day boundaries.
test_that("dashboard timestamps cover complete analysis days", {
  logs <- daily_activity_logs(analysis_days, analysis_examples, det_model_id = 10L)
  expect_equal(logs$date, analysis_days)
  expect_equal(as.numeric(logs$timestamp[1]), as.numeric(analysis_examples$start_time[1]))
  expect_equal(format(logs$timestamp, "%H:%M:%S", tz = analysis_timezone), rep("00:00:00", 3))
  expect_equal(as.numeric(analysis_day_starts(analysis_days[1] + 1)) - as.numeric(logs$timestamp[1]), 86400)
})

# AI-Generated
# Preserve camera identity and fill each camera's missing days.
test_that("camera activity keeps model counts and empty camera days separate", {
  logs <- camera_activity_logs(analysis_days, analysis_examples, analysis_cameras, det_model_id = 10L)
  expect_equal(nrow(logs), 6)
  expect_equal(logs$rat_count[logs$camera_id == 1L], c(2, 5, 0))
  expect_equal(logs$rat_count[logs$camera_id == 2L], c(3, 0, 0))
  expect_equal(sum(logs$other_count), 4)
  expect_equal(unique(logs$det_model_id), 10L)
})

# AI-Generated
# Return zero activity when the requested days have no observations.
test_that("an empty selected date range still produces zero-filled logs", {
  daily <- daily_activity_logs(analysis_days[3], analysis_examples, det_model_id = 10L)
  cameras <- camera_activity_logs(analysis_days[3], analysis_examples, analysis_cameras, det_model_id = 10L)
  expect_equal(daily$rat_count, 0)
  expect_equal(cameras$rat_count, c(0, 0))
  expect_equal(nrow(cameras), 2)
})

# AI-Generated
# Keep missing database results distinct from a day with zero activity.
test_that("empty analysis inputs do not fabricate observations", {
  expect_null(select_analysis_model(NULL))
  expect_null(daily_activity_logs(analysis_days, analysis_examples[FALSE, ]))
  expect_equal(nrow(camera_activity_logs(analysis_days, analysis_examples[FALSE, ], analysis_cameras)), 0)
})

# AI-Generated
# Preserve the model and stored values while converting Python analysis rows.
test_that("daily result conversion retains the detection model", {
  record <- list(id = 1L, camera_id = 1L, det_model_id = 10L, taxonomy_id = 3L,
    start_time = analysis_examples$start_time[1], end_time = analysis_examples$start_time[1] + 86400,
    taxonomy_count = 2L, avg_confidence = 0.9)
  converted <- daily_analysis_result_to_row(record)
  expect_identical(converted$det_model_id, 10L)
  expect_identical(converted$taxonomy_count, 2L)
  expect_equal(as.numeric(converted$start_time), as.numeric(record$start_time))
})

# AI-Generated
# Reuse scientific labels and assessed database roles for taxonomy rows.
test_that("taxonomy conversion preserves full names and unassessed roles", {
  rat <- taxonomy_to_row(list(id = 1L, genus = "Rattus", species = "Rattus rattus", is_predator = FALSE))
  predator <- taxonomy_to_row(list(id = 2L, genus = "Pavo", species = "cristatus", is_predator = TRUE))
  unassessed <- taxonomy_to_row(list(id = 3L, genus = "Mus", species = NULL, is_predator = NULL))
  expect_identical(rat$species_label, "Rattus rattus")
  expect_identical(predator$role, "predator")
  expect_identical(unassessed$role, "not assessed")
  expect_identical(rat$role, "prey")
})
