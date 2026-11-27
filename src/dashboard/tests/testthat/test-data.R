### Opportunity to smoke test catch mismatches between the DB and raw GUI-displayed data.


# Keep database counts and labels when loading dashboard data.
test_that("dashboard startup uses the supplied database records", {
  dashboard <- dashboard_test_data()
  expect_equal(dashboard$activity_logs$rat_count, c(5, 5))
  expect_equal(dashboard$camera_grid$camera_name, dashboard_test_cameras$camera_name)
  expect_identical(dashboard$valid_detection_labels, dashboard_test_annotations$species)
})

# Keep correction options available before a camera is opened.
test_that("startup loads species options independently of image records", {
  species <- c("Mus musculus", "Rattus rattus")
  dashboard <- dashboard_test_data(species = species)
  expect_false(exists("camera_images", dashboard, inherits = FALSE))
  expect_false(exists("detections", dashboard, inherits = FALSE))
  expect_identical(dashboard$valid_detection_labels, species)
})
