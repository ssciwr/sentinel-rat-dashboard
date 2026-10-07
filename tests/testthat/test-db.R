test_that("fetch_detections returns empty data frame initially", {
  result <- fetch_detections()
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 0)
})

test_that("predator_label maps is_predator to a role", {
  expect_equal(predator_label(TRUE), "predator")
  expect_equal(predator_label(FALSE), "prey")
  expect_equal(predator_label(NULL), "not assessed")
  expect_equal(predator_label(NA), "not assessed")
})

test_that("species_label prefers the common name", {
  expect_equal(species_label("Rattus", "rattus", "black rat"), "black rat")
  expect_equal(species_label("Rattus", "rattus", ""), "Rattus rattus")
  expect_equal(species_label("Rattus", "rattus"), "Rattus rattus")
  expect_equal(species_label("Rattus", "Rattus rattus"), "Rattus rattus")
  expect_equal(species_label("Rattus"), "Rattus")
})
