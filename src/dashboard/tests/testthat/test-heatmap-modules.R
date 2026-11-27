library(testthat)

setwd(normalizePath(file.path(getwd(), "../..")))
list2env(as.list(dashboard_test_data()), envir = environment())
source("R/functions.R", local = TRUE)
source("R/filters.R", local = TRUE)
source("R/heatmap.R", local = TRUE)

test_that("missing and unknown heatmap metrics fall back to rodent activity", {
  expect_equal(selected_heatmap_metric(NULL), "rodent")
  expect_equal(selected_heatmap_metric("bad"), "rodent")
  expect_equal(selected_heatmap_metric(""), "rodent")
  expect_equal(selected_heatmap_metric("rodent"), "rodent")
  expect_equal(selected_heatmap_metric("total"), "total")
})

test_that("the timeline initially selects rodent activity", {
  source("R/ui_controls.R", local = TRUE)
  source("ui/components/map_controls.R", local = TRUE)
  timeline <- xml2::read_html(as.character(map_timeline()))
  selected_view <- xml2::xml_find_all(timeline, "//button[@data-heatmap-metric and @aria-pressed='true']")
  expect_length(selected_view, 1)
  expect_identical(xml2::xml_attr(selected_view, "data-heatmap-metric"), "rodent")
  expect_identical(xml2::xml_text(selected_view), "Rodent activity")
})

test_that("ratio thresholds clamp percentage inputs", {
  expect_equal(ratio_threshold(50), 0.5)
  expect_equal(ratio_threshold(150), 1)
  expect_equal(ratio_threshold(-5), 0)
})

test_that("cell bounds produce ordered square extents", {
  cells <- heatmap_cell_bounds(data.frame(lat = c(6.55, 6.551), lon = c(80.2, 80.201)))
  expect_true(all(cells$cell_lat1 < cells$cell_lat2))
  expect_true(all(cells$cell_lon1 < cells$cell_lon2))
  expect_true(all(cells$cell_side_meters > 0))
})

test_that("map view starts at the first valid data point", {
  view <- map_view_from_data(data.frame(lat = c(NA, 6.55), lon = c(NA, 80.2)))
  expect_equal(view$lng, 80.2)
  expect_equal(view$lat, 6.55)
  expect_equal(view$zoom, map_initial_view$zoom)
})

test_that("predator palette increases across the pressure range", {
  colours <- predator_heat_colour(c(0, 0.5, 1))
  expect_equal(length(unique(colours)), 3)
})

test_that("contextual filters only expose the active metric", {
  settings <- heatmap_filter_settings("predator", FALSE, rodent_threshold = 90, predator_threshold = 40)
  expect_equal(settings$rodent_threshold, 0)
  expect_equal(settings$predator_threshold, 0.4)
})

# Thresholds get set to within 0-1 standardised range bfore building the map
test_that("grouped settings normalize extreme and missing thresholds", {
  settings <- heatmap_filter_settings("total", TRUE, predator_threshold = 150, rodent_threshold = -5, total_threshold = NULL)
  # This object gets passed to render the map and values in it should be squashed between 0 and 1.
  expect_equal(settings$predator_threshold, 1)
  expect_equal(settings$rodent_threshold, 0)
  expect_equal(settings$total_threshold, 0)
})
