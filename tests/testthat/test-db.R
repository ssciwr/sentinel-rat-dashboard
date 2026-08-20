test_that("fetch_analyses returns empty list initially", {
  result <- fetch_analyses()
  expect_s3_class(result, "data.frame")
  expect_nrow(result, 0)
})
