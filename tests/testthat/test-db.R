test_that("fetch_analyses returns empty data frame initially", {
  result <- fetch_analyses()
  expect_s3_class(result, "data.frame")
  expect_equal(nrow(result), 0)
})
